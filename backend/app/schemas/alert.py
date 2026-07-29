"""Alert Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import AlertSeverity, AlertStatus, AlertType


class AlertCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    alert_type: AlertType
    severity: AlertSeverity = AlertSeverity.MEDIUM
    camera_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None
    queue_id: Optional[uuid.UUID] = None
    extra_data: Optional[Dict[str, Any]] = None


class AlertAcknowledge(BaseModel):
    acknowledged_by: str = Field(..., min_length=1, max_length=150)


class AlertResolve(BaseModel):
    resolved_by: str = Field(..., min_length=1, max_length=150)
    resolution_note: Optional[str] = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    message: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    camera_id: Optional[uuid.UUID]
    zone_id: Optional[uuid.UUID]
    queue_id: Optional[uuid.UUID]
    extra_data: Optional[Dict[str, Any]]
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    resolution_note: Optional[str]
    created_at: datetime
    updated_at: datetime
