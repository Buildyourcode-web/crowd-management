"""Entry/Exit count and Zone count time-series models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDMixin


class EntryExitCount(Base, UUIDMixin):
    """Per-camera entry and exit count records (time-series)."""
    __tablename__ = "entry_exit_counts"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<EntryExitCount camera={self.camera_id} "
            f"entry={self.entry_count} exit={self.exit_count}>"
        )


class ZoneCount(Base, UUIDMixin):
    """Historical zone occupancy records."""
    __tablename__ = "zone_counts"

    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 'AI', 'MANUAL', 'SYNC'
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<ZoneCount zone={self.zone_id} count={self.count}>"
