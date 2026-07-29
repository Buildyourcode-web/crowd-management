"""Camera Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import CameraStatus, CameraType


class CameraCreate(BaseModel):
    camera_name: str = Field(..., min_length=1, max_length=150, description="Unique camera name")
    camera_type: CameraType
    rtsp_url: Optional[str] = Field(None, max_length=500, description="RTSP stream URL (Phase 2)")
    location: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    resolution: Optional[str] = Field(default="1920x1080", max_length=20)
    fps: int = Field(default=15, ge=1, le=120)
    zone_id: Optional[uuid.UUID] = None
    group_id: Optional[uuid.UUID] = None
    stream_enabled: bool = False
    ai_enabled: bool = False
    recording_enabled: bool = False

    @field_validator("rtsp_url", mode="before")
    @classmethod
    def validate_rtsp_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(("rtsp://", "rtsps://", "rtmp://")):
            raise ValueError("rtsp_url must start with rtsp://, rtsps://, or rtmp://")
        return v


class CameraUpdate(BaseModel):
    camera_name: Optional[str] = Field(None, min_length=1, max_length=150)
    camera_type: Optional[CameraType] = None
    rtsp_url: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    resolution: Optional[str] = Field(None, max_length=20)
    fps: Optional[int] = Field(None, ge=1, le=120)
    zone_id: Optional[uuid.UUID] = None
    group_id: Optional[uuid.UUID] = None
    stream_enabled: Optional[bool] = None
    ai_enabled: Optional[bool] = None
    recording_enabled: Optional[bool] = None


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_name: str
    camera_type: CameraType
    rtsp_url: Optional[str]
    location: Optional[str]
    description: Optional[str]
    resolution: Optional[str]
    fps: int
    status: CameraStatus
    is_active: bool
    stream_enabled: bool
    ai_enabled: bool
    recording_enabled: bool
    last_connected: Optional[datetime]
    last_frame_time: Optional[datetime]
    last_health_check: Optional[datetime]
    zone_id: Optional[uuid.UUID]
    group_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class CameraStatusUpdate(BaseModel):
    """Used for activate/deactivate endpoints."""
    is_active: bool
