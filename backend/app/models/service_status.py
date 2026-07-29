"""ServiceStatus model — tracks AI service health for dashboard display."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import ServiceName, ServiceStatusEnum
from app.database.base import Base, UUIDMixin


class ServiceStatus(Base, UUIDMixin):
    """
    One row per service. Updated in-place as status changes.
    Shows on dashboard: Person Service RUNNING | GPU 45% | Memory 2.1GB.
    """
    __tablename__ = "service_statuses"

    service_name: Mapped[ServiceName] = mapped_column(
        SAEnum(ServiceName, name="service_name_enum"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[ServiceStatusEnum] = mapped_column(
        SAEnum(ServiceStatusEnum, name="service_status_val_enum"),
        nullable=False,
        default=ServiceStatusEnum.STOPPED,
        index=True,
    )
    cpu_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    process_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<ServiceStatus name={self.service_name} status={self.status}>"
