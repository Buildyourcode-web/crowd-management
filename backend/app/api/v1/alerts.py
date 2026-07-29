"""Alert API endpoints."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import AlertSeverity
from app.common.response import ApiResponse, PagedResponse
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.schemas.alert import (
    AlertAcknowledge,
    AlertCreate,
    AlertResolve,
    AlertResponse,
)
from app.services.alert.alert_service import AlertService
from app.utils.pagination import get_pagination, PaginationParams

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)) -> AlertService:
    return AlertService(db)


@router.post(
    "",
    response_model=ApiResponse[AlertResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create alert",
)
async def create_alert(
    data: AlertCreate,
    request: Request,
    service: AlertService = Depends(get_service),
):
    alert = await service.create_alert(data)
    return ApiResponse.created(
        data=AlertResponse.model_validate(alert),
        message="Alert created",
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "",
    response_model=PagedResponse[AlertResponse],
    summary="List alerts",
)
async def list_alerts(
    request: Request,
    open_only: bool = Query(default=False),
    severity: Optional[AlertSeverity] = Query(default=None),
    pagination: PaginationParams = Depends(get_pagination),
    service: AlertService = Depends(get_service),
):
    alerts = await service.list_alerts(
        skip=pagination.offset,
        limit=pagination.page_size,
        open_only=open_only,
        severity=severity,
    )
    total = await service.count_open_alerts() if open_only else len(alerts)
    return PagedResponse.build(
        data=[AlertResponse.model_validate(a) for a in alerts],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{alert_id}",
    response_model=ApiResponse[AlertResponse],
    summary="Get alert",
)
async def get_alert(
    alert_id: uuid.UUID,
    request: Request,
    service: AlertService = Depends(get_service),
):
    alert = await service.get_alert(alert_id)
    return ApiResponse.ok(
        data=AlertResponse.model_validate(alert),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/{alert_id}/acknowledge",
    response_model=ApiResponse[AlertResponse],
    summary="Acknowledge alert",
)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    data: AlertAcknowledge,
    request: Request,
    service: AlertService = Depends(get_service),
):
    alert = await service.acknowledge_alert(alert_id, data)
    return ApiResponse.ok(
        data=AlertResponse.model_validate(alert),
        message="Alert acknowledged",
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/{alert_id}/resolve",
    response_model=ApiResponse[AlertResponse],
    summary="Resolve alert",
)
async def resolve_alert(
    alert_id: uuid.UUID,
    data: AlertResolve,
    request: Request,
    service: AlertService = Depends(get_service),
):
    alert = await service.resolve_alert(alert_id, data)
    return ApiResponse.ok(
        data=AlertResponse.model_validate(alert),
        message="Alert resolved",
        request_id=getattr(request.state, "request_id", None),
    )
