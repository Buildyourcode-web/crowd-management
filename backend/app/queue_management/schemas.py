"""
Queue Management Pydantic schemas — 5-level system.

Separates API data contracts from business logic.
"""
from typing import Optional
from pydantic import BaseModel, Field


class QueueROIConfig(BaseModel):
    """
    Rectangle ROI configuration for one queue camera.

    Coordinates are in absolute pixel values of the camera frame.
    (x1, y1) = top-left corner of the queue area.
    (x2, y2) = bottom-right corner of the queue area.

    Example — queue spanning centre of a 1280×720 frame:
        {"x1": 100, "y1": 200, "x2": 900, "y2": 650}
    """
    x1: float = Field(..., description="Top-left X in pixels")
    y1: float = Field(..., description="Top-left Y in pixels")
    x2: float = Field(..., description="Bottom-right X in pixels")
    y2: float = Field(..., description="Bottom-right Y in pixels")
    direction: str = Field(
        default="UP",
        description="Queue movement direction: UP | DOWN | LEFT | RIGHT | ANY"
    )
    stabilization_sec: float = Field(
        default=3.0,
        ge=0.5,
        le=30.0,
        description="Health state must hold this many seconds before UI updates (0.5–30s)"
    )


class QueueStatus(BaseModel):
    """
    Live queue snapshot for one camera — all 5 levels.

    Returned by GET /api/v1/queue/status/{camera_id}
    and published to Redis channel:queue.status whenever metrics change.

    Level 1 — Occupancy
        people_inside_queue  persons whose centroid is inside the ROI
        queue_length         same as people_inside_queue
        queue_status         EMPTY | LOW | MEDIUM | HIGH

    Level 2 — Movement
        movement_px          average pixels moved per tracked person this frame

    Level 3 — Speed
        speed_px_per_sec     EMA-smoothed speed in pixels / second

    Level 4 — Health
        queue_health         MOVING | SLOW | VERY SLOW | BLOCKED | EMPTY

    Level 5 — Stagnation
        stagnation_seconds   how long queue has been BLOCKED (speed < 2 px/s)
        stagnation_label     OK | BLOCKED | CRITICAL
    """
    camera_id: str
    worker_running: bool = False

    # Level 1 — Occupancy
    people_inside_queue: int = 0
    queue_length: int = 0
    queue_status: str = "EMPTY"

    # Level 2 — Movement
    movement_px: float = 0.0
    forward_movers: int = 0    # people with meaningful forward progress this frame
    tracked_people: int = 0    # people with position history this frame
    progress_ratio: float = 0.0

    # Level 3 — Speed
    speed_px_per_sec: float = 0.0

    # Level 4 — Health
    queue_health: str = "UNKNOWN"
    # pending_health intentionally omitted from public schema (internal/debug only)

    # Level 5 — Stagnation
    stagnation_seconds: float = 0.0
    stagnation_label: str = "OK"

    # Meta
    queue_direction: str = "UP"
    fps: float = 0.0
    last_updated: Optional[str] = None
