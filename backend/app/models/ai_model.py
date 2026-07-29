"""AIModel registry — tracks available models for Phase 2 inference."""
from typing import Optional

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import AIModelType
from app.database.base import Base, TimestampMixin, UUIDMixin


class AIModel(Base, UUIDMixin, TimestampMixin):
    """
    Registry of AI models.
    Example: YOLO11x v1.0, confidence=0.5, iou=0.45, active=True
    Makes model version updates easy without code changes.
    """
    __tablename__ = "ai_models"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_type: Mapped[AIModelType] = mapped_column(
        SAEnum(AIModelType, name="ai_model_type_enum"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    iou: Mapped[float] = mapped_column(Float, nullable=False, default=0.45)
    input_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_loaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<AIModel name={self.name} version={self.version} "
            f"active={self.is_active}>"
        )
