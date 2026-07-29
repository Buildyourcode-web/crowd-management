"""Camera model — physical camera configuration and state."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import CameraStatus, CameraType
from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.camera_group import CameraGroup
    from app.models.camera_health import CameraHealth
    from app.models.roi import ROI
    from app.models.zone import Zone


class Camera(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cameras"

    camera_name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    camera_type: Mapped[CameraType] = mapped_column(
        SAEnum(CameraType, name="camera_type_enum"), nullable=False, index=True
    )
    rtsp_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resolution and performance
    resolution: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default="1920x1080"
    )
    fps: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    # Status
    status: Mapped[CameraStatus] = mapped_column(
        SAEnum(CameraStatus, name="camera_status_enum"),
        nullable=False,
        default=CameraStatus.OFFLINE,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    # Phase 2 feature flags (infrastructure ready — not activated in Phase 1)
    stream_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recording_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Connectivity timestamps
    last_connected: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_frame_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_health_check: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Foreign keys
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("camera_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    zone: Mapped[Optional["Zone"]] = relationship("Zone", back_populates="cameras")
    group: Mapped[Optional["CameraGroup"]] = relationship(
        "CameraGroup", back_populates="cameras"
    )
    health_records: Mapped[List["CameraHealth"]] = relationship(
        "CameraHealth", back_populates="camera", lazy="select", cascade="all, delete-orphan"
    )
    rois: Mapped[List["ROI"]] = relationship(
        "ROI", back_populates="camera", lazy="select", cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="camera", lazy="select", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Camera id={self.id} name={self.camera_name} "
            f"type={self.camera_type} status={self.status}>"
        )
