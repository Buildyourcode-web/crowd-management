"""
FrameBuffer — in-memory store for the latest frame per camera.

Only ONE frame per camera is kept at any time.
No video is stored or written to disk.
"""
import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import numpy as np


@dataclass
class FrameEntry:
    """Snapshot of a camera's most recent captured frame."""

    camera_id: uuid.UUID
    latest_frame: Optional[np.ndarray]  # BGR frame array from OpenCV
    timestamp: Optional[datetime]       # UTC time the frame was stored
    fps: float = 0.0                    # Measured streaming FPS
    frame_number: int = 0               # Monotonically increasing per-camera counter (debug/monitoring)


class FrameBuffer:
    """
    Thread-safe in-memory dictionary: camera_id (str) -> FrameEntry.

    Uses asyncio.Lock so that multiple coroutines can safely read/write
    without data races. All public methods are async.
    """

    def __init__(self) -> None:
        self._buffer: Dict[str, FrameEntry] = {}
        self._frame_counters: Dict[str, int] = {}  # per-camera frame_number tracking
        self._lock: asyncio.Lock = asyncio.Lock()

    # ─── Write ────────────────────────────────────────────────────────────────

    async def update(
        self,
        camera_id: uuid.UUID,
        frame: Optional[np.ndarray],
        fps: float,
    ) -> None:
        """Replace (or create) the latest frame entry for a camera, incrementing frame_number."""
        async with self._lock:
            key = str(camera_id)
            frame_number = self._frame_counters.get(key, 0) + 1
            self._frame_counters[key] = frame_number
            self._buffer[key] = FrameEntry(
                camera_id=camera_id,
                latest_frame=frame,
                timestamp=datetime.utcnow(),
                fps=round(fps, 2),
                frame_number=frame_number,
            )

    async def remove(self, camera_id: uuid.UUID) -> None:
        """Remove one camera's entry and its frame counter. Does not affect other cameras."""
        async with self._lock:
            key = str(camera_id)
            self._buffer.pop(key, None)
            self._frame_counters.pop(key, None)

    async def clear(self) -> None:
        """Flush ALL entries and counters safely — for use during application shutdown."""
        async with self._lock:
            self._buffer.clear()
            self._frame_counters.clear()

    # ─── Read ─────────────────────────────────────────────────────────────────

    async def exists(self, camera_id: uuid.UUID) -> bool:
        """Return True if a frame entry exists for the given camera, False otherwise."""
        async with self._lock:
            return str(camera_id) in self._buffer

    async def get(self, camera_id: uuid.UUID) -> Optional[FrameEntry]:
        """Return the latest FrameEntry for a camera, or None if not present."""
        async with self._lock:
            return self._buffer.get(str(camera_id))

    async def all_entries(self) -> Dict[str, FrameEntry]:
        """Return a shallow copy of the entire buffer (safe to iterate)."""
        async with self._lock:
            return dict(self._buffer)

    async def camera_ids(self) -> list:
        """Return list of camera_id strings currently in the buffer."""
        async with self._lock:
            return list(self._buffer.keys())
