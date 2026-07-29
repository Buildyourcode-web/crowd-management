"""CameraRepository — all camera database operations."""
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera import Camera
from app.common.enums import CameraStatus, CameraType
from app.repositories.base import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Camera, session)

    async def get_by_name(self, camera_name: str) -> Optional[Camera]:
        result = await self.session.execute(
            select(Camera).where(Camera.camera_name == camera_name)
        )
        return result.scalar_one_or_none()

    async def get_active_cameras(self) -> List[Camera]:
        result = await self.session.execute(
            select(Camera)
            .where(Camera.is_active == True)  # noqa: E712
            .order_by(Camera.camera_name)
        )
        return list(result.scalars().all())

    async def get_by_zone(
        self, zone_id: uuid.UUID, active_only: bool = True
    ) -> List[Camera]:
        stmt = select(Camera).where(Camera.zone_id == zone_id)
        if active_only:
            stmt = stmt.where(Camera.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(
        self, camera_type: CameraType, active_only: bool = True
    ) -> List[Camera]:
        stmt = select(Camera).where(Camera.camera_type == camera_type)
        if active_only:
            stmt = stmt.where(Camera.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_group(
        self, group_id: uuid.UUID, active_only: bool = True
    ) -> List[Camera]:
        stmt = select(Camera).where(Camera.group_id == group_id)
        if active_only:
            stmt = stmt.where(Camera.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self, camera: Camera, status: CameraStatus
    ) -> Camera:
        camera.status = status
        self.session.add(camera)
        await self.session.flush()
        await self.session.refresh(camera)
        return camera

    async def count_active(self) -> int:
        return await self.count(Camera.is_active == True)  # noqa: E712

    async def count_by_status(self, status: CameraStatus) -> int:
        return await self.count(Camera.status == status)
