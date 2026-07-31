"""
PersonTracker — ByteTrack integration (Task 2).

═══════════════════════════════════════════════════════════════════════
Architecture
═══════════════════════════════════════════════════════════════════════

Each PersonCounterWorker owns ONE PersonTracker instance.
The tracker is per-camera — its BYTETracker object holds the tracking
state (active tracks, lost tracks, track IDs) for ONLY that camera.

Detection is performed by the shared YOLO model (ModelManager singleton).
Tracking is CPU-only and lightweight — no GPU contention between cameras.

    Camera 1 Worker ──→ PersonTracker(bt1) ──┐
    Camera 2 Worker ──→ PersonTracker(bt2) ──┤  → separate ByteTrack states
    Camera N Worker ──→ PersonTracker(btN) ──┘

This design allows N cameras to run simultaneously without tracker
state bleeding between cameras.

═══════════════════════════════════════════════════════════════════════
How ByteTrack works (Ultralytics 8.x)
═══════════════════════════════════════════════════════════════════════

1. High-confidence detections (> track_high_thresh) are linked to existing
   tracks via Hungarian algorithm using IoU.
2. Unmatched tracks are re-associated with low-confidence detections.
3. Still-unmatched tracks enter a "lost" state for up to track_buffer
   frames. If they reappear, the same track_id is restored.
4. After track_buffer frames of absence, the track is deleted.

Result: each person keeps the SAME integer track_id as long as they
are visible (or briefly occluded).

═══════════════════════════════════════════════════════════════════════
Detection filtering
═══════════════════════════════════════════════════════════════════════

model() is called with classes=[0] (COCO class 0 = person).
Non-person objects are never passed to the tracker — this reduces
unnecessary track churn and speeds up the Hungarian matching step.
"""
from dataclasses import dataclass
from typing import Any, List, Optional

import numpy as np
from loguru import logger

from app.ai.model_manager import model_manager

# COCO dataset class index for "person"
PERSON_CLASS_ID: int = 0

# Graceful import — BYTETracker is part of ultralytics which we verified
# is installed, but we guard anyway so the rest of the app never crashes.
try:
    from ultralytics.trackers.byte_tracker import BYTETracker
    from ultralytics.utils import IterableSimpleNamespace

    _BYTETRACK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _BYTETRACK_AVAILABLE = False
    logger.warning("BYTETracker not importable — person tracking disabled")


# ─── Data model ───────────────────────────────────────────────────────────────


@dataclass
class TrackedPerson:
    """
    A detected person with a stable cross-frame identity.

    track_id is assigned by BYTETracker and is stable while the person
    is visible or temporarily lost (up to track_buffer frames).
    """

    track_id: int
    x1: float       # Bounding box: top-left x
    y1: float       # Bounding box: top-left y
    x2: float       # Bounding box: bottom-right x
    y2: float       # Bounding box: bottom-right y
    confidence: float = 0.0

    @property
    def cx(self) -> float:
        """Horizontal centre of the bounding box."""
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        """Vertical centre of the bounding box (used for line crossing)."""
        return (self.y1 + self.y2) / 2.0


# ─── Tracker ──────────────────────────────────────────────────────────────────


class PersonTracker:
    """
    Per-camera ByteTrack wrapper.

    Usage (synchronous — always call from a thread executor):
        tracker = PersonTracker(frame_rate=10)
        persons = tracker.update(frame)   # List[TrackedPerson]

    Internal pipeline:
        model(frame, classes=[0]) → Results → BYTETracker.update() → tracks
    """

    def __init__(self, frame_rate: int = 10) -> None:
        self._frame_rate = frame_rate
        self._tracker: Optional[Any] = None
        self._latest_tracked: List[TrackedPerson] = []

        if not _BYTETRACK_AVAILABLE:
            return

        # BYTETracker configuration.
        # track_high_thresh: detections above this are "high quality" (linked first)
        # track_low_thresh:  detections above this can recover lost tracks
        # new_track_thresh:  minimum score to create a brand-new track
        # track_buffer:      frames a track survives without a detection
        #                    (≈ frame_rate * seconds_to_keep_lost_track)
        # match_thresh:      maximum IoU distance to link detection ↔ track
        cfg = IterableSimpleNamespace(
            tracker_type="bytetrack",
            track_high_thresh=0.35,   # was 0.50 — link detections even on confidence dips
            track_low_thresh=0.10,
            new_track_thresh=0.35,    # was 0.50 — same, prevents spurious new IDs
            track_buffer=90,          # keep lost tracks for ~9 s at 10 fps
            match_thresh=0.75,        # was 0.85 — more lenient IoU re-linking
            fuse_score=True,
        )
        # BYTETracker.__init__(args) — only takes the args namespace, no frame_rate kwarg
        self._tracker = BYTETracker(cfg)
        logger.debug(
            "PersonTracker initialised | frame_rate={fr}", fr=frame_rate
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, frame: np.ndarray) -> List[TrackedPerson]:
        """
        Detect persons in the frame and update ByteTrack.

        Synchronous / blocking — must be called from asyncio.to_thread().

        Args:
            frame: BGR numpy array from the camera's FrameBuffer.

        Returns:
            List of TrackedPerson with stable track IDs.
            Empty list if the model is not loaded, tracker unavailable,
            no persons detected, or any error occurs.
        """
        if self._tracker is None:
            return []

        model = model_manager.get_model()
        if model is None:
            logger.warning("PersonTracker.update(): model not loaded")
            return []

        # ── Step 1: Person-only detection ─────────────────────────────────────
        # Calling model() directly (not detector.detect()) so we can filter
        # to class 0 before tracking — reduces tracker overhead significantly.
        # This reuses the same loaded model instance (never reloads).
        try:
            results = model(
                frame,
                classes=[PERSON_CLASS_ID],
                imgsz=640,
                conf=0.35,
                iou=0.45,
                verbose=False,
            )
        except Exception as exc:
            logger.error(
                "PersonTracker detection failed | {err}", err=str(exc)
            )
            return []

        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            # No persons in frame — update tracker with empty detections
            # so lost tracks age out correctly.
            try:
                empty_boxes = results[0].boxes if results else None
                if empty_boxes is not None:
                    self._tracker.update(empty_boxes.cpu(), frame)
                else:
                    self._tracker.update(np.empty((0, 6)), frame)
            except Exception:
                pass
            self._latest_tracked = []
            return []

        # ── Step 2: BYTETracker update ────────────────────────────────────────
        # Pass results[0].boxes.cpu() — BYTETracker needs CPU tensors,
        # YOLO11 runs on cuda:0 so tensors must be moved to host memory first.
        try:
            tracks = self._tracker.update(results[0].boxes.cpu(), frame)
        except Exception as exc:
            logger.error(
                "BYTETracker.update() failed | {err}", err=str(exc)
            )
            return []

        if tracks is None or len(tracks) == 0:
            return []

        # ── Step 3: Parse track output ────────────────────────────────────────
        # BYTETracker returns numpy array shape (N, 8):
        #   [x1, y1, x2, y2, track_id, confidence, class_id, det_index]
        persons: List[TrackedPerson] = []
        for track in tracks:
            if len(track) < 5:
                continue  # Malformed row — skip safely
            cls_id = int(track[6]) if len(track) > 6 else PERSON_CLASS_ID
            if cls_id != PERSON_CLASS_ID:
                continue  # Should not happen (we called with classes=[0])
            persons.append(
                TrackedPerson(
                    track_id=int(track[4]),
                    x1=float(track[0]),
                    y1=float(track[1]),
                    x2=float(track[2]),
                    y2=float(track[3]),
                    confidence=float(track[5]) if len(track) > 5 else 0.0,
                )
            )

        self._latest_tracked = persons
        return persons
