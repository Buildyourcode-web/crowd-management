"""Zone Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Unique zone name")
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    capacity: int = Field(default=500, ge=1, description="Maximum person capacity")
    warning_threshold: int = Field(default=400, ge=1)
    critical_threshold: int = Field(default=475, ge=1)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_thresholds(self) -> "ZoneCreate":
        if self.warning_threshold >= self.critical_threshold:
            raise ValueError("warning_threshold must be less than critical_threshold")
        if self.critical_threshold > self.capacity:
            raise ValueError("critical_threshold cannot exceed capacity")
        return self


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    capacity: Optional[int] = Field(None, ge=1)
    warning_threshold: Optional[int] = Field(None, ge=1)
    critical_threshold: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    location: Optional[str]
    capacity: int
    warning_threshold: int
    critical_threshold: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
