"""Event model — unified event log for all system events."""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import EventSeverity, EventType
from app.database.base import Base, UUIDMixin


class Event(Base, UUIDMixin):
    """
    Unified event log — every significant system event recorded here.
    Primary source for dashboard history.
    Covers: Queue Alert, Zone Alert, Camera Offline, Face Match, Entry Closed, etc.
    """
    __tablename__ = "events"

    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, name="event_type_enum"),
        nullable=False,
        index=True,
    )
    severity: Mapped[EventSeverity] = mapped_column(
        SAEnum(EventSeverity, name="event_severity_enum"),
        nullable=False,
        default=EventSeverity.INFO,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # All source references are optional
    camera_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    queue_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_acknowledged: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    acknowledged_by: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<Event type={self.event_type} severity={self.severity}>"
        )
