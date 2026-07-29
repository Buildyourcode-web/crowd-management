"""
Face Recognition Pydantic schemas — Phase 7.

Separates API data contracts from business logic.
"""
from typing import Optional
from pydantic import BaseModel, Field


class FaceWorkerStatus(BaseModel):
    """Live status for one camera's face recognition worker."""

    camera_id: str
    worker_running: bool = False
    faces_detected_total: int = 0
    matches_total: int = 0
    unknowns_total: int = 0
    fps: float = 0.0
    threshold: float = 0.55
    last_updated: Optional[str] = None


class PersonRecord(BaseModel):
    """Registered person — returned by GET /face/persons."""

    person_id: str
    name: str
    status: str = "active"
    created_at: Optional[str] = None
