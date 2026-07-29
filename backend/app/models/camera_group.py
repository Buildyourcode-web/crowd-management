"""CameraGroup model — groups cameras by purpose (Entry, Exit, Queue, Temple, Face)."""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera import Camera


class CameraGroup(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "camera_groups"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cameras: Mapped[List["Camera"]] = relationship(
        "Camera", back_populates="group", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<CameraGroup id={self.id} name={self.name}>"
