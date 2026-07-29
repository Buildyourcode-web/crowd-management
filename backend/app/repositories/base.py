"""Generic async CRUD repository base."""
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Provides generic async CRUD operations for a SQLAlchemy model."""

    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, record_id: Any) -> Optional[ModelT]:
        """Fetch a single record by primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        order_by: Optional[Any] = None,
    ) -> List[ModelT]:
        """Fetch all records with optional pagination and ordering."""
        stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *filters: Any) -> int:
        """Count records, optionally filtered."""
        stmt = select(func.count()).select_from(self.model)
        for f in filters:
            stmt = stmt.where(f)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, obj: ModelT) -> ModelT:
        """Persist a new record. Caller owns flush/commit."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelT, data: dict) -> ModelT:
        """Apply a dict of field updates to an existing record."""
        for field, value in data.items():
            if hasattr(obj, field) and value is not None:
                setattr(obj, field, value)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        """Delete a record from the database."""
        await self.session.delete(obj)
        await self.session.flush()

    async def exists(self, *filters: Any) -> bool:
        """Return True if at least one record matches the filters."""
        stmt = select(func.count()).select_from(self.model)
        for f in filters:
            stmt = stmt.where(f)
        result = await self.session.execute(stmt)
        return (result.scalar_one() or 0) > 0
