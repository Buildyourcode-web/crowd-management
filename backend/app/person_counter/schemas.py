"""
Person Counter Pydantic schemas — Phase 4.

Separates data contracts (API request/response) from business logic.
"""
from typing import Optional

from pydantic import BaseModel, Field


class CountingLineConfig(BaseModel):
    """
    Virtual counting line coordinates in absolute pixel values.

    The line direction determines Entry/Exit semantics:

    Horizontal line (|dx| >= |dy|)
        Draw left → right across the frame.
        Top  → Bottom = Entry  (y increases downward in image coords)
        Bottom → Top = Exit

    Vertical line (|dy| > |dx|)
        Draw top → bottom down the frame.
        Left → Right = Entry
        Right → Left = Exit

    Examples:
        Horizontal line at y=360 across a 1280-wide frame:
            {"start_x": 0, "start_y": 360, "end_x": 1280, "end_y": 360}

        Vertical line at x=640 down a 720-tall frame:
            {"start_x": 640, "start_y": 0, "end_x": 640, "end_y": 720}
    """

    start_x: float = Field(..., description="Line start X in pixels")
    start_y: float = Field(..., description="Line start Y in pixels")
    end_x: float = Field(..., description="Line end X in pixels")
    end_y: float = Field(..., description="Line end Y in pixels")


class PersonCountStatus(BaseModel):
    """
    Live count snapshot for one camera.

    Returned by GET /api/v1/person-counter/status/{camera_id}
    and published to Redis channel:person.count whenever counts change.
    """

    camera_id: str
    entry_count: int = 0           # Cumulative persons who entered
    exit_count: int = 0            # Cumulative persons who exited
    current_occupancy: int = 0     # max(0, entry - exit)
    worker_running: bool = False
    fps: float = 0.0               # Measured inference FPS of this worker
    last_updated: Optional[str] = None  # ISO-8601 UTC timestamp
