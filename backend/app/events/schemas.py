"""
Event schemas for the Live Communication Layer.

Every event published over Redis and broadcast over WebSocket
uses the same envelope: LiveEvent.
"""
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field


# ─── Event Type Constants ─────────────────────────────────────────────────────

class EventType:
    """
    String constants for all live event types.
    String (not Enum) for easy extensibility across phases.
    """

    # Camera lifecycle
    CAMERA_CONNECTED    = "camera.connected"
    CAMERA_DISCONNECTED = "camera.disconnected"
    CAMERA_RESTARTED    = "camera.restarted"
    CAMERA_HEALTH_UPDATED = "camera.health_updated"

    # System
    SYSTEM_STARTUP  = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR    = "system.error"


# ─── Event Envelope ───────────────────────────────────────────────────────────

class LiveEvent(BaseModel):
    """
    Universal event envelope.

    All events published to Redis and broadcast over WebSocket
    share this exact structure — no exceptions.

    Example JSON:
    {
        "event_type": "camera.connected",
        "source":     "camera_manager",
        "timestamp":  "2026-07-24T17:00:00+00:00",
        "payload": {
            "camera_id": "uuid-...",
            "status":    "ONLINE",
            "fps":       15.0
        }
    }
    """

    event_type: str
    source: str = "temple_ai"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    payload: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict suitable for WebSocket broadcast."""
        return self.model_dump()

    def to_json(self) -> str:
        """Return compact JSON string for Redis publish."""
        return self.model_dump_json()
