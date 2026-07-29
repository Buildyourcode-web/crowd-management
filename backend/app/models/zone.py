"""Zone model — physical areas within the temple premises."""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera import Camera
    from app.models.alert import Alert


class Zone(Base, UUIDMixin, TimestampMixin):
    """
    Represents a physical zone in the temple.
    NOTE: current occupancy count is stored in Redis (not here).
          Only historical counts are stored in ZoneCount table.
    """
    __tablename__ = "zones"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Capacity management
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    warning_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=400)
    critical_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=475)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cameras: Mapped[List["Camera"]] = relationship(
        "Camera", back_populates="zone", lazy="select"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="zone", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Zone id={self.id} name={self.name} capacity={self.capacity}>"
