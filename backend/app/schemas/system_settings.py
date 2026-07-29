"""SystemSettings Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SystemSettingsCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, description="Setting key (unique)")
    value: Optional[str] = None
    value_type: str = Field(
        default="string",
        pattern="^(string|int|float|bool|json)$",
        description="Data type of the value",
    )
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    is_public: bool = False


class SystemSettingsUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    is_public: Optional[bool] = None
    updated_by: Optional[str] = Field(None, max_length=150)


class SystemSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    value: Optional[str]
    value_type: str
    description: Optional[str]
    category: Optional[str]
    is_public: bool
    updated_by: Optional[str]
    created_at: datetime
    updated_at: datetime
