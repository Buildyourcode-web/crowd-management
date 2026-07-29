"""CriminalWatchlist and FaceDetectionLog models."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin


class CriminalWatchlist(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "criminal_watchlist"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    case_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True
    )
    face_embedding: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    face_image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    threat_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_by: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    detections: Mapped[List["FaceDetectionLog"]] = relationship(
        "FaceDetectionLog", back_populates="watchlist_entry", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<CriminalWatchlist id={self.id} name={self.name}>"


class FaceDetectionLog(Base, UUIDMixin):
    __tablename__ = "face_detection_logs"

    watchlist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("criminal_watchlist.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    face_image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bounding_box: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    watchlist_entry: Mapped[Optional["CriminalWatchlist"]] = relationship(
        "CriminalWatchlist", back_populates="detections"
    )

    def __repr__(self) -> str:
        return (
            f"<FaceDetectionLog camera={self.camera_id} matched={self.matched}>"
        )
