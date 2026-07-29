"""
Face Database — KnownPerson ORM model + FaceDatabase manager (Tasks 1, 2).

═══════════════════════════════════════════════════════════════════════
Database schema (Task 2)
═══════════════════════════════════════════════════════════════════════

Table: known_persons

    id               UUID (PK, gen_random_uuid())
    person_id        VARCHAR UNIQUE NOT NULL (e.g. "P102")
    name             VARCHAR NOT NULL (e.g. "John Doe")
    reference_image  BYTEA   NULLABLE (raw JPEG bytes of the registration photo)
    embedding        BYTEA   NOT NULL (512 × float32 = 2048 bytes)
    status           VARCHAR NOT NULL DEFAULT "active"
    created_at       TIMESTAMPTZ NOT NULL (auto)
    updated_at       TIMESTAMPTZ NOT NULL (auto-updated)

Embedding is stored as raw float32 bytes (serialize/deserialize from
embedding.py). No pgvector extension required.

═══════════════════════════════════════════════════════════════════════
In-memory cache (Task 1)
═══════════════════════════════════════════════════════════════════════

FaceDatabase maintains a dict:
    _cache: {person_id → (name, normalized_embedding)}

The cache is ALWAYS used for recognition — never query PostgreSQL per frame.
PostgreSQL is used only for:
    - Persistence across restarts
    - CRUD operations (register / update / delete)
    - reload() to refresh the cache after manual DB changes

═══════════════════════════════════════════════════════════════════════
Initialization
═══════════════════════════════════════════════════════════════════════

face_database.ensure_initialized() is called by:
    - POST /face/register    (before first registration)
    - POST /face/start/{camera_id}  (before first worker starts)

It creates the known_persons table if it doesn't exist, then loads
all "active" persons into the in-memory cache. Idempotent.
"""
import asyncio
import threading
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import LargeBinary

from app.database.base import Base, UUIDMixin, TimestampMixin
from app.database.connection import AsyncSessionLocal, async_engine
from app.face_recognition.embedding import deserialize_embedding, normalize_embedding


# ─── ORM Model ───────────────────────────────────────────────────────────────


class KnownPerson(Base, UUIDMixin, TimestampMixin):
    """
    SQLAlchemy ORM model for the known_persons table.

    Embedding is stored as raw float32 bytes (LargeBinary).
    512 dimensions × 4 bytes = 2048 bytes per row.
    """

    __tablename__ = "known_persons"

    person_id: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    reference_image: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True, comment="Raw JPEG bytes of registration photo"
    )
    embedding: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        comment="512-dim float32 ArcFace embedding (2048 bytes)",
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="active", server_default="active"
    )


# ─── FaceDatabase ─────────────────────────────────────────────────────────────


class FaceDatabase:
    """
    Known-person embedding manager.

    Combines PostgreSQL persistence with an in-memory embedding cache.

    CRUD flow:
        register / update / delete → write to PostgreSQL → update cache
        reload()                   → re-read PostgreSQL → replace cache
        get_all_for_matching()     → read from cache (O(1), no DB hit)

    All public methods except get_all_for_matching() are async.
    """

    def __init__(self) -> None:
        # Cache: person_id → (name, normalized_embedding)
        self._cache: Dict[str, Tuple[str, np.ndarray]] = {}
        self._initialized: bool = False
        self._init_lock = threading.Lock()

    # ── Initialization ────────────────────────────────────────────────────────

    async def ensure_initialized(self) -> None:
        """
        Create table (if needed) and load all active persons into cache.
        Idempotent — safe to call multiple times.
        """
        with self._init_lock:
            if self._initialized:
                return
        await self._create_table()
        await self._load_cache()
        self._initialized = True

    async def _create_table(self) -> None:
        """Create known_persons table if it doesn't exist."""
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: KnownPerson.__table__.create(
                        sync_conn, checkfirst=True
                    )
                )
            logger.info("FaceDatabase | known_persons table ready")
        except Exception as exc:
            logger.error(
                "FaceDatabase | Table creation failed | {err}", err=str(exc)
            )
            raise

    async def _load_cache(self) -> None:
        """Load all active persons from PostgreSQL into the in-memory cache."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(KnownPerson).where(KnownPerson.status == "active")
                )
                persons = result.scalars().all()

            self._cache = {
                p.person_id: (
                    p.name,
                    normalize_embedding(deserialize_embedding(p.embedding)),
                )
                for p in persons
            }
            logger.info(
                "FaceDatabase | Cache loaded | persons={n}", n=len(self._cache)
            )
        except Exception as exc:
            logger.error(
                "FaceDatabase | Cache load failed | {err}", err=str(exc)
            )
            raise

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def register(
        self,
        person_id: str,
        name: str,
        embedding_bytes: bytes,
        image_bytes: Optional[bytes] = None,
    ) -> None:
        """
        Persist a new person and add them to the in-memory cache.

        Raises ValueError if person_id already exists.
        """
        if person_id in self._cache:
            raise ValueError(f"person_id '{person_id}' already exists")

        async with AsyncSessionLocal() as session:
            person = KnownPerson(
                person_id=person_id,
                name=name,
                embedding=embedding_bytes,
                reference_image=image_bytes,
                status="active",
            )
            session.add(person)
            await session.commit()

        # Update in-memory cache immediately
        self._cache[person_id] = (
            name,
            normalize_embedding(deserialize_embedding(embedding_bytes)),
        )
        logger.info(
            "FaceDatabase | Registered | person_id={pid} | name={n}",
            pid=person_id,
            n=name,
        )

    async def update(
        self,
        person_id: str,
        name: Optional[str] = None,
        embedding_bytes: Optional[bytes] = None,
        image_bytes: Optional[bytes] = None,
    ) -> bool:
        """
        Update an existing person's name and/or embedding.

        Returns True if found and updated, False if not found.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(KnownPerson).where(KnownPerson.person_id == person_id)
            )
            person = result.scalar_one_or_none()
            if person is None:
                return False

            if name is not None:
                person.name = name
            if embedding_bytes is not None:
                person.embedding = embedding_bytes
            if image_bytes is not None:
                person.reference_image = image_bytes

            await session.commit()

        # Sync cache
        if person_id in self._cache:
            old_name, old_emb = self._cache[person_id]
            updated_name = name if name is not None else old_name
            updated_emb = (
                normalize_embedding(deserialize_embedding(embedding_bytes))
                if embedding_bytes is not None
                else old_emb
            )
            self._cache[person_id] = (updated_name, updated_emb)

        logger.info(
            "FaceDatabase | Updated | person_id={pid}", pid=person_id
        )
        return True

    async def delete(self, person_id: str) -> bool:
        """
        Remove a person from database and cache.

        Returns True if deleted, False if not found.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(KnownPerson).where(KnownPerson.person_id == person_id)
            )
            person = result.scalar_one_or_none()
            if person is None:
                return False
            await session.delete(person)
            await session.commit()

        self._cache.pop(person_id, None)
        logger.info(
            "FaceDatabase | Deleted | person_id={pid}", pid=person_id
        )
        return True

    async def reload(self) -> int:
        """
        Force-reload the in-memory cache from PostgreSQL.

        Returns number of persons now in cache.
        Useful after manual DB edits or external changes.
        """
        await self._load_cache()
        count = len(self._cache)
        logger.info("FaceDatabase | Cache reloaded | persons={n}", n=count)
        return count

    # ── Read (in-memory only) ─────────────────────────────────────────────────

    def get_all_for_matching(self) -> List[Tuple[str, str, np.ndarray]]:
        """
        Return cached embeddings for live recognition.

        Returns:
            List of (person_id, name, normalized_embedding).
            Never queries PostgreSQL — always from in-memory cache.
            Safe to call from a thread executor.
        """
        return [
            (pid, name, emb)
            for pid, (name, emb) in self._cache.items()
        ]

    def exists(self, person_id: str) -> bool:
        """Return True if person_id is in the cache."""
        return person_id in self._cache

    @property
    def count(self) -> int:
        """Number of persons currently in the in-memory cache."""
        return len(self._cache)

    async def get_all_persons(self) -> List[dict]:
        """
        Return all registered persons (active and inactive) without embeddings.
        Used by GET /face/persons endpoint.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(KnownPerson).order_by(KnownPerson.created_at.desc())
            )
            persons = result.scalars().all()
            return [
                {
                    "person_id":  p.person_id,
                    "name":       p.name,
                    "status":     p.status,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in persons
            ]


# ─── Singleton ────────────────────────────────────────────────────────────────

face_database: FaceDatabase = FaceDatabase()
