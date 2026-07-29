"""SystemSettings model — configurable key/value system parameters."""
from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class SystemSettings(Base, UUIDMixin, TimestampMixin):
    """
    Key-value store for system-wide configurable settings.
    Prevents hardcoding detection parameters (FPS, confidence, IOU, intervals).

    Example rows:
        key=DETECTION_FPS          value=5       value_type=int    category=AI
        key=DEFAULT_CONFIDENCE     value=0.5     value_type=float  category=AI
        key=DEFAULT_IOU            value=0.45    value_type=float  category=AI
        key=ALERT_INTERVAL         value=300     value_type=int    category=ALERT
        key=SNAPSHOT_INTERVAL      value=30      value_type=int    category=SNAPSHOT
    """
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="string"
    )  # string | int | float | bool | json
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # AI | ALERT | SNAPSHOT | SYSTEM
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Exposed on /version or /metrics
    updated_by: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemSettings key={self.key} value={self.value}>"
