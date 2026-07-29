"""ZoneRepository — all zone database operations."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.zone import Zone
from app.repositories.base import BaseRepository


class ZoneRepository(BaseRepository[Zone]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Zone, session)

    async def get_by_name(self, name: str) -> Optional[Zone]:
        result = await self.session.execute(
            select(Zone).where(Zone.name == name)
        )
        return result.scalar_one_or_none()

    async def get_active_zones(self) -> List[Zone]:
        result = await self.session.execute(
            select(Zone)
            .where(Zone.is_active == True)  # noqa: E712
            .order_by(Zone.name)
        )
        return list(result.scalars().all())

    async def get_with_cameras(self, zone_id: object) -> Optional[Zone]:
        result = await self.session.execute(
            select(Zone)
            .where(Zone.id == zone_id)
            .options(selectinload(Zone.cameras))
        )
        return result.scalar_one_or_none()
