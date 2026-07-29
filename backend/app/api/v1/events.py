"""Events API endpoints — unified event log."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.common.enums import EventSeverity, EventType
from app.common.exceptions import EventNotFoundException
from app.common.response import ApiResponse, PagedResponse
from app.database.connection import get_db
from app.models.event import Event
from app.repositories.event import EventRepository
from app.schemas.event import EventCreate, EventAcknowledge, EventResponse
from app.utils.pagination import get_pagination, PaginationParams

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[EventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Log event",
)
async def create_event(
    data: EventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    repo = EventRepository(db)
    event = Event(
        event_type=data.event_type,
        severity=data.severity,
        title=data.title,
        description=data.description,
        extra_data=data.extra_data,
        camera_id=data.camera_id,
        zone_id=data.zone_id,
        queue_id=data.queue_id,
        alert_id=data.alert_id,
        occurred_at=data.occurred_at or datetime.now(timezone.utc),
    )
    event = await repo.create(event)
    return ApiResponse.created(
        data=EventResponse.model_validate(event),
        message="Event logged",
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "",
    response_model=PagedResponse[EventResponse],
    summary="List events",
)
async def list_events(
    request: Request,
    severity: Optional[EventSeverity] = Query(default=None),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    repo = EventRepository(db)
    events = await repo.get_recent(
        limit=pagination.page_size, severity=severity
    )
    total = await repo.count()
    return PagedResponse.build(
        data=[EventResponse.model_validate(e) for e in events],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{event_id}",
    response_model=ApiResponse[EventResponse],
    summary="Get event",
)
async def get_event(
    event_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    repo = EventRepository(db)
    event = await repo.get_by_id(event_id)
    if not event:
        raise EventNotFoundException(event_id)
    return ApiResponse.ok(
        data=EventResponse.model_validate(event),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/{event_id}/acknowledge",
    response_model=ApiResponse[EventResponse],
    summary="Acknowledge event",
)
async def acknowledge_event(
    event_id: uuid.UUID,
    data: EventAcknowledge,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    repo = EventRepository(db)
    event = await repo.get_by_id(event_id)
    if not event:
        raise EventNotFoundException(event_id)
    event = await repo.acknowledge_event(event, data.acknowledged_by)
    return ApiResponse.ok(
        data=EventResponse.model_validate(event),
        message="Event acknowledged",
        request_id=getattr(request.state, "request_id", None),
    )
