"""Zone API endpoints."""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ZoneNotFoundException, ConflictException
from app.common.response import ApiResponse, PagedResponse
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.zone import Zone
from app.repositories.zone import ZoneRepository
from app.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate
from app.utils.pagination import get_pagination, PaginationParams

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[ZoneResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create zone",
)
async def create_zone(
    data: ZoneCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    repo = ZoneRepository(db)
    existing = await repo.get_by_name(data.name)
    if existing:
        raise ConflictException("Zone", "name", data.name)
    zone = Zone(**data.model_dump())
    zone = await repo.create(zone)
    return ApiResponse.created(
        data=ZoneResponse.model_validate(zone),
        message="Zone created successfully",
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "",
    response_model=PagedResponse[ZoneResponse],
    summary="List zones",
)
async def list_zones(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    repo = ZoneRepository(db)
    zones = await repo.get_all(skip=pagination.offset, limit=pagination.page_size)
    total = await repo.count()
    return PagedResponse.build(
        data=[ZoneResponse.model_validate(z) for z in zones],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{zone_id}",
    response_model=ApiResponse[ZoneResponse],
    summary="Get zone",
)
async def get_zone(
    zone_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    repo = ZoneRepository(db)
    zone = await repo.get_by_id(zone_id)
    if not zone:
        raise ZoneNotFoundException(zone_id)
    return ApiResponse.ok(
        data=ZoneResponse.model_validate(zone),
        request_id=getattr(request.state, "request_id", None),
    )


@router.put(
    "/{zone_id}",
    response_model=ApiResponse[ZoneResponse],
    summary="Update zone",
)
async def update_zone(
    zone_id: uuid.UUID,
    data: ZoneUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    repo = ZoneRepository(db)
    zone = await repo.get_by_id(zone_id)
    if not zone:
        raise ZoneNotFoundException(zone_id)
    update_data = data.model_dump(exclude_none=True)
    zone = await repo.update(zone, update_data)
    return ApiResponse.ok(
        data=ZoneResponse.model_validate(zone),
        message="Zone updated",
        request_id=getattr(request.state, "request_id", None),
    )


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete zone",
)
async def delete_zone(
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    repo = ZoneRepository(db)
    zone = await repo.get_by_id(zone_id)
    if not zone:
        raise ZoneNotFoundException(zone_id)
    await repo.delete(zone)
