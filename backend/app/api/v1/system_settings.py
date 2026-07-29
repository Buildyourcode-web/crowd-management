"""System Settings API endpoints."""
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.common.exceptions import ConflictException, SystemSettingsNotFoundException
from app.common.response import ApiResponse, PagedResponse
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.system_settings import SystemSettings
from app.repositories.base import BaseRepository
from app.schemas.system_settings import (
    SystemSettingsCreate,
    SystemSettingsResponse,
    SystemSettingsUpdate,
)
from app.utils.pagination import get_pagination, PaginationParams

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[SystemSettingsResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create setting",
)
async def create_setting(
    data: SystemSettingsCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from sqlalchemy import select
    existing = await db.execute(
        select(SystemSettings).where(SystemSettings.key == data.key)
    )
    if existing.scalar_one_or_none():
        raise ConflictException("SystemSettings", "key", data.key)
    setting = SystemSettings(**data.model_dump())
    db.add(setting)
    await db.flush()
    await db.refresh(setting)
    return ApiResponse.created(
        data=SystemSettingsResponse.model_validate(setting),
        message="Setting created",
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "",
    response_model=PagedResponse[SystemSettingsResponse],
    summary="List settings",
)
async def list_settings(
    request: Request,
    category: Optional[str] = Query(default=None),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, func
    stmt = select(SystemSettings)
    if category:
        stmt = stmt.where(SystemSettings.category == category)
    count_stmt = select(func.count()).select_from(SystemSettings)
    if category:
        count_stmt = count_stmt.where(SystemSettings.category == category)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    result = await db.execute(
        stmt.offset(pagination.offset).limit(pagination.page_size)
    )
    settings_list = result.scalars().all()
    return PagedResponse.build(
        data=[SystemSettingsResponse.model_validate(s) for s in settings_list],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{setting_id}",
    response_model=ApiResponse[SystemSettingsResponse],
    summary="Get setting",
)
async def get_setting(
    setting_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.id == setting_id)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise SystemSettingsNotFoundException(setting_id)
    return ApiResponse.ok(
        data=SystemSettingsResponse.model_validate(setting),
        request_id=getattr(request.state, "request_id", None),
    )


@router.put(
    "/{setting_id}",
    response_model=ApiResponse[SystemSettingsResponse],
    summary="Update setting",
)
async def update_setting(
    setting_id: uuid.UUID,
    data: SystemSettingsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.id == setting_id)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise SystemSettingsNotFoundException(setting_id)
    update_data = data.model_dump(exclude_none=True)
    update_data["updated_by"] = current_user.get("username", "anonymous")
    for field, value in update_data.items():
        setattr(setting, field, value)
    db.add(setting)
    await db.flush()
    await db.refresh(setting)
    return ApiResponse.ok(
        data=SystemSettingsResponse.model_validate(setting),
        message="Setting updated",
        request_id=getattr(request.state, "request_id", None),
    )
