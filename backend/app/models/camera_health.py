"""CameraHealth — periodic health snapshots per camera."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera import Camera


class CameraHealth(Base, UUIDMixin):
    __tablename__ = "camera_health"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cpu_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # percent
    memory_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # percent
    gpu_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # percent (Phase 2)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)          # frames/sec
    decode_fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # decode FPS (Phase 2)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    packet_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # percent
    bitrate_kbps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    camera: Mapped["Camera"] = relationship("Camera", back_populates="health_records")

    def __repr__(self) -> str:
        return (
            f"<CameraHealth camera={self.camera_id} "
            f"fps={self.fps} cpu={self.cpu_usage}>"
        )
