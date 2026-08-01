"""Async PostgreSQL connection management via SQLAlchemy 2.0 + asyncpg."""
import time
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.common.exceptions import DatabaseConnectionException
from app.config.settings import settings

# ─── Engine ───────────────────────────────────────────────────────────────────

async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_recycle=settings.POSTGRES_POOL_RECYCLE,
    pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─── Dependency ───────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding a scoped AsyncSession.
    Commits on success, rolls back on any exception, always closes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── Health Probe ─────────────────────────────────────────────────────────────

async def check_db_health() -> dict:
    """
    Lightweight DB health probe. Returns latency and status.
    Raises DatabaseConnectionException on failure.
    """
    start = time.monotonic()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        logger.debug("DB health OK | latency={l}ms", l=latency_ms)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        logger.error("DB health FAILED | error={e}", e=str(exc))
        raise DatabaseConnectionException(detail=str(exc)) from exc


# ─── Lifecycle Hooks ──────────────────────────────────────────────────────────

async def connect_db() -> None:
    """Warm up the connection pool at startup and ensure all DB tables exist."""
    try:
        health = await check_db_health()
        logger.info("Database connected | {h}", h=health)

        # Auto-create database tables if not yet created
        async with async_engine.begin() as conn:
            from app.database.base import Base
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified/created successfully")
    except Exception as exc:
        logger.critical("Cannot reach database on startup: {e}", e=str(exc))
        raise


async def disconnect_db() -> None:
    """Gracefully dispose the async engine on shutdown."""
    await async_engine.dispose()
    logger.info("Database connection pool disposed")
