"""ROI (Region of Interest) model — polygon-based regions on camera feeds."""
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import ROIDirection, ROIType
from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera import Camera


class ROI(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "rois"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    roi_type: Mapped[ROIType] = mapped_column(
        SAEnum(ROIType, name="roi_type_enum"), nullable=False
    )
    direction: Mapped[ROIDirection] = mapped_column(
        SAEnum(ROIDirection, name="roi_direction_enum"),
        nullable=False,
        default=ROIDirection.BOTH,
    )
    # Polygon stored as list of [x, y] coordinate pairs: [[x1,y1],[x2,y2],...]
    polygon: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    camera: Mapped["Camera"] = relationship("Camera", back_populates="rois")

    def __repr__(self) -> str:
        return (
            f"<ROI id={self.id} name={self.name} "
            f"type={self.roi_type} dir={self.direction}>"
        )
