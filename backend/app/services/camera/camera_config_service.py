"""Camera Configuration Service — Phase 1.

Responsibilities: Add, Edit, Delete, Activate, Deactivate cameras.
NO RTSP connection. NO streaming. RTSP belongs to Phase 2.
"""
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import CameraStatus
from app.common.exceptions import (
    CameraAlreadyExistsException,
    CameraNotFoundException,
)
from app.models.camera import Camera
from app.repositories.camera import CameraRepository
from app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate


class CameraConfigService:
    """
    Manages camera configuration lifecycle.
    Only concerns itself with configuration — not streaming or AI.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = CameraRepository(session)

    async def add_camera(self, data: CameraCreate) -> Camera:
        """Add a new camera configuration to the system."""
        existing = await self._repo.get_by_name(data.camera_name)
        if existing:
            raise CameraAlreadyExistsException("camera_name", data.camera_name)

        camera = Camera(
            camera_name=data.camera_name,
            camera_type=data.camera_type,
            rtsp_url=data.rtsp_url,
            location=data.location,
            description=data.description,
            resolution=data.resolution,
            fps=data.fps,
            zone_id=data.zone_id,
            group_id=data.group_id,
            stream_enabled=data.stream_enabled,
            ai_enabled=data.ai_enabled,
            recording_enabled=data.recording_enabled,
            status=CameraStatus.OFFLINE,
            is_active=False,
        )
        camera = await self._repo.create(camera)
        logger.info("Camera added | name={name} | type={t}", name=camera.camera_name, t=camera.camera_type)
        return camera

    async def get_camera(self, camera_id: uuid.UUID) -> Camera:
        """Fetch a camera by ID or raise CameraNotFoundException."""
        camera = await self._repo.get_by_id(camera_id)
        if not camera:
            raise CameraNotFoundException(camera_id)
        return camera

    async def list_cameras(
        self,
        skip: int = 0,
        limit: int = 20,
        active_only: bool = False,
    ) -> List[Camera]:
        """List cameras with optional active filter."""
        if active_only:
            return await self._repo.get_active_cameras()
        return await self._repo.get_all(skip=skip, limit=limit)

    async def count_cameras(self, active_only: bool = False) -> int:
        if active_only:
            return await self._repo.count_active()
        return await self._repo.count()

    async def edit_camera(
        self, camera_id: uuid.UUID, data: CameraUpdate
    ) -> Camera:
        """Update camera configuration fields."""
        camera = await self.get_camera(camera_id)

        # Check name uniqueness if being changed
        if data.camera_name and data.camera_name != camera.camera_name:
            existing = await self._repo.get_by_name(data.camera_name)
            if existing:
                raise CameraAlreadyExistsException("camera_name", data.camera_name)

        update_data = data.model_dump(exclude_none=True)
        camera = await self._repo.update(camera, update_data)
        logger.info(
            "Camera updated | id={id} | fields={fields}",
            id=camera_id,
            fields=list(update_data.keys()),
        )
        return camera

    async def delete_camera(self, camera_id: uuid.UUID) -> None:
        """Remove a camera from the system."""
        camera = await self.get_camera(camera_id)
        camera_name = camera.camera_name
        await self._repo.delete(camera)
        logger.info("Camera deleted | id={id} | name={name}", id=camera_id, name=camera_name)

    async def activate_camera(self, camera_id: uuid.UUID) -> Camera:
        """Mark a camera as active (is_active=True, status=OFFLINE)."""
        camera = await self.get_camera(camera_id)
        camera.is_active = True
        camera.status = CameraStatus.OFFLINE  # Stream connection happens in Phase 2
        self._repo.session.add(camera)
        await self._repo.session.flush()
        await self._repo.session.refresh(camera)
        logger.info("Camera activated | id={id}", id=camera_id)
        return camera

    async def deactivate_camera(self, camera_id: uuid.UUID) -> Camera:
        """Mark a camera as inactive (is_active=False, status=OFFLINE)."""
        camera = await self.get_camera(camera_id)
        camera.is_active = False
        camera.status = CameraStatus.OFFLINE
        self._repo.session.add(camera)
        await self._repo.session.flush()
        await self._repo.session.refresh(camera)
        logger.info("Camera deactivated | id={id}", id=camera_id)
        return camera
