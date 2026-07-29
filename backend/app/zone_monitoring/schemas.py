"""
Zone Monitoring Pydantic schemas — Phase 6.

Separates API data contracts from business logic.
All validation (Task 15) is enforced here via Pydantic validators.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ZoneConfig(BaseModel):
    """
    Configuration for a single rectangular zone.

    Coordinates are absolute pixel values of the camera frame.
    (x1, y1) = top-left corner, (x2, y2) = bottom-right corner.

    Validation rules (Task 15):
        - All coordinates must be >= 0
        - x1 != x2  (width > 0)
        - y1 != y2  (height > 0)
        - zone_id must be non-empty
    """

    zone_id: str = Field(..., description="Unique zone identifier (e.g. 'A', 'entrance')")
    zone_name: str = Field(..., description="Human-readable zone name")
    x1: float = Field(..., ge=0, description="Top-left X in pixels")
    y1: float = Field(..., ge=0, description="Top-left Y in pixels")
    x2: float = Field(..., ge=0, description="Bottom-right X in pixels")
    y2: float = Field(..., ge=0, description="Bottom-right Y in pixels")

    @field_validator("zone_id")
    @classmethod
    def zone_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("zone_id must not be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_dimensions(self) -> "ZoneConfig":
        if abs(self.x2 - self.x1) < 1:
            raise ValueError(
                f"Zone '{self.zone_id}': x1={self.x1} and x2={self.x2} produce zero width"
            )
        if abs(self.y2 - self.y1) < 1:
            raise ValueError(
                f"Zone '{self.zone_id}': y1={self.y1} and y2={self.y2} produce zero height"
            )
        return self


class ZoneStartRequest(BaseModel):
    """
    Request body for POST /zone/start/{camera_id}.

    Accepts 1 or more zone configurations.
    Duplicate zone_ids are rejected.

    Example:
    ```json
    {
        "zones": [
            {"zone_id": "A", "zone_name": "Entrance", "x1": 120, "y1": 150, "x2": 640, "y2": 540},
            {"zone_id": "B", "zone_name": "Exit",     "x1": 650, "y1": 150, "x2": 1200,"y2": 540}
        ]
    }
    ```
    """

    zones: List[ZoneConfig] = Field(..., min_length=1, description="At least one zone required")

    @model_validator(mode="after")
    def no_duplicate_zone_ids(self) -> "ZoneStartRequest":
        ids = [z.zone_id for z in self.zones]
        duplicates = {z for z in ids if ids.count(z) > 1}
        if duplicates:
            raise ValueError(f"Duplicate zone_ids: {sorted(duplicates)}")
        return self


class ZoneMetrics(BaseModel):
    """
    Live metrics for one zone (included in ZoneCameraStatus).

    Fields:
        people_count  — persons detected inside this zone
        density       — people_count / (zone_area / 1000), i.e. people per 1000 px²
        status        — EMPTY | LOW | MEDIUM | HIGH | CRITICAL
    """

    zone_id: str
    zone_name: str
    people_count: int = 0
    density: float = 0.0
    status: str = "EMPTY"


class ZoneCameraStatus(BaseModel):
    """
    Live status for all zones of one camera.

    Returned by GET /api/v1/zone/status/{camera_id}
    and published to Redis channel:zone.status on any change.
    """

    camera_id: str
    worker_running: bool = False
    zones: List[ZoneMetrics] = Field(default_factory=list)
    fps: float = 0.0
    last_updated: Optional[str] = None
