"""Event Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import EventSeverity, EventType


class EventCreate(BaseModel):
    event_type: EventType
    severity: EventSeverity = EventSeverity.INFO
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    camera_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None
    queue_id: Optional[uuid.UUID] = None
    alert_id: Optional[uuid.UUID] = None
    occurred_at: Optional[datetime] = None


class EventAcknowledge(BaseModel):
    acknowledged_by: str = Field(..., min_length=1, max_length=150)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: EventType
    severity: EventSeverity
    title: str
    description: Optional[str]
    extra_data: Optional[Dict[str, Any]]
    camera_id: Optional[uuid.UUID]
    zone_id: Optional[uuid.UUID]
    queue_id: Optional[uuid.UUID]
    alert_id: Optional[uuid.UUID]
    is_acknowledged: bool
    acknowledged_by: Optional[str]
    occurred_at: datetime
