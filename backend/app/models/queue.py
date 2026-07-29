"""Queue and QueueSnapshot models."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import QueueStatusEnum
from app.database.base import Base, TimestampMixin, UUIDMixin


class Queue(Base, UUIDMixin, TimestampMixin):
    """Physical queue at an entry/exit point."""
    __tablename__ = "queues"

    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    camera_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    snapshots: Mapped[List["QueueSnapshot"]] = relationship(
        "QueueSnapshot", back_populates="queue", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Queue id={self.id} name={self.name}>"


class QueueSnapshot(Base, UUIDMixin):
    """
    Point-in-time snapshot of queue state.
    Live state is served from Redis; this table stores historical snapshots.
    """
    __tablename__ = "queue_snapshots"

    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    people: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    waiting_time: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # seconds
    status: Mapped[QueueStatusEnum] = mapped_column(
        SAEnum(QueueStatusEnum, name="queue_status_enum"),
        nullable=False,
        default=QueueStatusEnum.NORMAL,
        index=True,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    queue: Mapped["Queue"] = relationship("Queue", back_populates="snapshots")

    def __repr__(self) -> str:
        return (
            f"<QueueSnapshot queue={self.queue_id} "
            f"people={self.people} status={self.status}>"
        )
