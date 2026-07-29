"""CameraGroup Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CameraGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique group name")
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class CameraGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class CameraGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    location: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
