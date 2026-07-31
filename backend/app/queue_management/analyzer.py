"""
QueueAnalyzer — Full 5-level queue analysis engine.

═══════════════════════════════════════════════════════════════════════
Levels
═══════════════════════════════════════════════════════════════════════

  Level 1 – Occupancy          people_inside_queue, queue_status (EMPTY/LOW/MEDIUM/HIGH)
  Level 2 – Movement           median pixels moved per person this frame (direction-projected)
  Level 3 – Speed              movement_px / elapsed_seconds  (px/sec, EMA-smoothed)
  Level 4 – Queue Health       MOVING / SLOW / VERY SLOW   (3 states, no BLOCKED)
  Level 5 – Alert Engine       stagnation_label: OK / BLOCKED / CRITICAL

═══════════════════════════════════════════════════════════════════════
Health / Speed thresholds
═══════════════════════════════════════════════════════════════════════

  > 20 px/sec  → MOVING
  10–20        → SLOW
  ≤ 10         → VERY SLOW    (previously split at 2px/s into VERY SLOW + BLOCKED)

═══════════════════════════════════════════════════════════════════════
Alert Engine (stagnation_label) — driven by VERY_SLOW_THRESHOLD
═══════════════════════════════════════════════════════════════════════

  speed < ALERT_SPEED_THRESHOLD (2.0 px/s) continuously:
    < 30 sec  → stagnation_label = OK
    30s–2min  → stagnation_label = BLOCKED   (alert!)
    > 2 min   → stagnation_label = CRITICAL  (alert!)
"""
import math
import statistics
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from app.ai.model_manager import model_manager
from app.person_counter.tracker import PersonTracker, TrackedPerson
from app.queue_management.roi import QueueROI

# ─── Jitter filter (Level 2) ─────────────────────────────────────────────────

JITTER_THRESHOLD_PX: float = 5.0
# Movements smaller than this are treated as 0.
# Eliminates YOLO bounding-box jitter from small body sway / head movement.
# Common production setting — keeps speed≈0 for truly stationary queues.

# ─── Queue direction vectors (Level 2 improvement) ────────────────────────────
# Maps a direction label to its unit vector (dx, dy) in image coordinates.
# Image convention: Y increases downward, X increases rightward.
#
#   UP    → people walk toward smaller Y  (0, -1)
#   DOWN  → people walk toward larger  Y  (0, +1)
#   LEFT  → people walk toward smaller X  (-1, 0)
#   RIGHT → people walk toward larger  X  (+1, 0)
#   ANY   → use Euclidean distance (no directional filter)
#
# Only the forward component of each track's displacement is counted.
# Side steps, head turns, shoulder sways → projection ≈ 0 → filtered out.
# Backward steps  → projection < 0 → clamped to 0.

DIRECTION_VECTORS: dict = {
    "UP":    (0.0, -1.0),
    "DOWN":  (0.0,  1.0),
    "LEFT": (-1.0,  0.0),
    "RIGHT": (1.0,  0.0),
    "ANY":   None,          # fallback: Euclidean distance
}

DEFAULT_QUEUE_DIRECTION: str = "UP"  # most temple queues move toward the gate

# ─── Occupancy thresholds (Level 1) ──────────────────────────────────────────

DEFAULT_LOW_MAX: int = 10     # 1–10  → LOW
DEFAULT_MEDIUM_MAX: int = 25  # 11–25 → MEDIUM
                               # 26+   → HIGH

# ─── Speed thresholds px/sec (Levels 3 & 4) ──────────────────────────────────

SPEED_MOVING_MIN: float = 20.0      # > 20  → MOVING
SPEED_SLOW_MIN: float = 10.0        # 10–20 → SLOW
ALERT_SPEED_THRESHOLD: float = 2.0
# Speed below which the stagnation ALERT timer starts accumulating.
# Intentionally SEPARATE from SPEED_SLOW_MIN (10 px/s) used for health.
#
# Why separate?
#   Speed = 6 px/s  → health = VERY SLOW  (correct)
#                   → 6 > 2, timer does NOT start  (correct, not an alert)
#
#   Speed = 0.5 px/s → health = VERY SLOW  (correct)
#                    → 0.5 < 2, timer starts  (correct — almost zero movement)
#   After 30s continuous: stagnation_label = BLOCKED
#
# Field calibration:
#   Tune SPEED_SLOW_MIN  to adjust when health shows VERY SLOW vs SLOW.
#   Tune ALERT_SPEED_THRESHOLD to adjust how strict the blockage alert trigger is.

SPEED_SMOOTHING_WINDOW: int = 6     # EMA window (frames)

# ─── Stagnation thresholds (Level 5) ─────────────────────────────────────────

STAGNATION_BLOCKED_SEC: float = 30.0    # 30s  → BLOCKED
STAGNATION_CRITICAL_SEC: float = 120.0  # 2min → CRITICAL

# ─── Health stabilization (prevents rapid flicker) ───────────────────────────

HEALTH_STABILIZATION_SEC: float = 3.0
# New health state must hold for this many seconds before being officially
# adopted. Prevents rapid MOVING→BLOCKED→MOVING color changes caused by
# one person taking a small step then stopping.
# EMPTY is exempted — it takes effect immediately when count drops to 0.

HEALTH_RECOVERY_SEC: float = 1.0
# When health IMPROVES (e.g. VERY SLOW → MOVING), adopt the better state
# after only this many seconds of confirmation.
# Must be shorter than HEALTH_STABILIZATION_SEC to allow fast recovery.

# ─── Health state ranking (for asymmetric stabilization) ──────────────────────

HEALTH_ORDER: dict = {
    "MOVING":    3,   # best
    "SLOW":      2,
    "VERY SLOW": 1,
    "EMPTY":     0,
    "UNKNOWN":   0,
    # BLOCKED intentionally absent — no longer a health state.
    # BLOCKED only appears in stagnation_label (alert engine).
}
# Comparing rank(new) vs rank(current):
#   new_rank > current_rank  → IMPROVEMENT  → use HEALTH_RECOVERY_SEC (1s)
#   new_rank <= current_rank → DEGRADATION  → use HEALTH_STABILIZATION_SEC (3s)

# ─── Progress ratio threshold ─────────────────────────────────────────────────

PROGRESS_RATIO_THRESHOLD: float = 0.30
# If fewer than 30% of tracked people are making forward progress,
# the queue is considered stagnant regardless of average speed.
# Example: 1 out of 10 people stepped forward → average 2.5px/s → VERY SLOW,
# but progress_ratio = 0.10 → too few people moving → exposed as a metric.


# ─── Pure functions ───────────────────────────────────────────────────────────

DEFAULT_MIN_PEOPLE_FOR_BLOCKAGE: int = 2
# Minimum people in queue for the stagnation ALERT to apply.
# 0 people → EMPTY, 1 person → not a queue, 2+ people → alert eligible.
# Note: this no longer gates health (which is now purely speed-based),
# only gates the stagnation timer so a lone standing person
# does not trigger a BLOCKED or CRITICAL alert.


# ─── Pure functions ───────────────────────────────────────────────────────────

def get_queue_status(
    count: int,
    low_max: int = DEFAULT_LOW_MAX,
    medium_max: int = DEFAULT_MEDIUM_MAX,
) -> str:
    """Map person count to queue occupancy status string (Level 1)."""
    if count == 0:
        return "EMPTY"
    if count <= low_max:
        return "LOW"
    if count <= medium_max:
        return "MEDIUM"
    return "HIGH"


def get_queue_health(speed_px_per_sec: float) -> str:
    """Map smoothed speed to a queue health label (Level 4).

    Returns one of three states only:
      MOVING    — queue flowing normally
      SLOW      — queue moving but sluggish
      VERY SLOW — queue barely moving or stopped

    BLOCKED is intentionally NOT returned here.
    Blockage is an ALERT raised by the stagnation engine (Level 5)
    when speed < VERY_SLOW_THRESHOLD continuously for 30+ seconds.
    """
    if speed_px_per_sec > SPEED_MOVING_MIN:
        return "MOVING"
    if speed_px_per_sec > SPEED_SLOW_MIN:
        return "SLOW"
    return "VERY SLOW"  # covers 0–10 px/s (previously split at 2px/s)


def get_stagnation_label(stagnation_seconds: float) -> str:
    """Map stagnation duration to an urgency label (Level 5)."""
    if stagnation_seconds >= STAGNATION_CRITICAL_SEC:
        return "CRITICAL"
    if stagnation_seconds >= STAGNATION_BLOCKED_SEC:
        return "BLOCKED"
    return "OK"


# ─── QueueAnalyzer ────────────────────────────────────────────────────────────

class QueueAnalyzer:
    """
    Per-camera queue analysis engine (all 5 levels).

    Stateful — owns a PersonTracker (ByteTrack) to maintain track IDs
    across frames, enabling movement and speed calculations.

    One QueueAnalyzer per QueueWorker (one per camera).

    Usage (synchronous — call from asyncio.to_thread):
        analyzer = QueueAnalyzer(roi)
        metrics  = analyzer.analyze(frame)

    Returns a dict with keys:
        people_inside_queue  int
        queue_length         int   (== people_inside_queue)
        queue_status         str   EMPTY | LOW | MEDIUM | HIGH
        movement_px          float avg px moved this frame
        speed_px_per_sec     float EMA-smoothed speed
        queue_health         str   MOVING | SLOW | VERY SLOW | BLOCKED
        stagnation_seconds   float how long queue has been BLOCKED
        stagnation_label     str   OK | BLOCKED | CRITICAL
        inference_ms         float YOLO latency
    """

    def __init__(
        self,
        roi: QueueROI,
        low_max: int = DEFAULT_LOW_MAX,
        medium_max: int = DEFAULT_MEDIUM_MAX,
        tracker_fps: int = 5,
        jitter_threshold: float = JITTER_THRESHOLD_PX,
        min_people_for_blockage: int = DEFAULT_MIN_PEOPLE_FOR_BLOCKAGE,
        direction: str = DEFAULT_QUEUE_DIRECTION,
        stabilization_sec: float = HEALTH_STABILIZATION_SEC,
    ) -> None:
        self._roi = roi
        self._low_max = low_max
        self._medium_max = medium_max
        self._jitter_threshold = jitter_threshold
        self._min_people_for_blockage = min_people_for_blockage
        self._stabilization_sec = stabilization_sec  # configurable per-instance
        # Resolve direction to unit vector (None = ANY = Euclidean)
        self._direction = direction.upper()
        self._direction_vec = DIRECTION_VECTORS.get(self._direction, None)

        # ByteTrack wrapper — same as PersonCounter but independent instance
        self._tracker = PersonTracker(frame_rate=tracker_fps)

        # ── Level 2 / 3: movement & speed ────────────────────────────────────
        self._prev_positions: Dict[int, Tuple[float, float]] = {}
        self._prev_time: float = time.monotonic()
        self._speed_window: Deque[float] = deque(maxlen=SPEED_SMOOTHING_WINDOW)

        # ── Level 2 / 3 computed values ───────────────────────────────────────
        self._movement_px: float = 0.0
        self._speed_px_per_sec: float = 0.0

        # ── Level 4 ───────────────────────────────────────────────────────────
        self._queue_health: str = "UNKNOWN"

        # ── Level 5: stagnation timer ─────────────────────────────────────────
        # _stagnation_start is set when speed drops below SPEED_VERY_SLOW_MIN.
        # It is cleared when speed recovers above that threshold.
        self._stagnation_start: Optional[float] = None
        self._stagnation_seconds: float = 0.0

        # ── Health stabilization ──────────────────────────────────────────────
        # _pending_health tracks what raw health has been for how long.
        # _queue_health (the official stable state) only updates after
        # HEALTH_STABILIZATION_SEC of holding the same pending value.
        self._pending_health: str = "UNKNOWN"
        self._pending_since: float = time.monotonic()

        # ── Progress ratio ────────────────────────────────────────────────────
        self._progress_ratio: float = 0.0
        self._forward_movers: int = 0    # people with meaningful forward progress
        self._tracked_people: int = 0   # people with position history this frame
        # Fraction of tracked persons making meaningful forward progress (0–1).

    # ── Private helpers ───────────────────────────────────────────────────────

    def _forward_progress(self, dx: float, dy: float) -> float:
        """
        Compute forward progress of a track movement (dx, dy).

        If a queue direction is set:
            Project (dx, dy) onto the direction unit vector.
            Head turns   → dx large, dy small → projection ≈ 0 → filtered out.
            Side steps   → perpendicular        → projection = 0 → filtered out.
            Forward step → along direction      → projection = distance → counted.
            Backward     → opposite direction   → projection < 0 → clamped to 0.

        If direction is ANY:
            Use Euclidean distance (backward compatible).

        Jitter filter applied last: values < jitter_threshold treated as 0.
        """
        if self._direction_vec is None:
            # ANY direction — Euclidean
            raw = math.hypot(dx, dy)
        else:
            fx, fy = self._direction_vec
            # Dot product = projection onto forward axis
            raw = dx * fx + dy * fy
            # Backward movement = 0 (not negative speed)
            raw = max(0.0, raw)

        # Jitter filter: sub-threshold movement = noise
        return raw if raw >= self._jitter_threshold else 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Run one analysis pass on a camera frame.

        Synchronous / blocking — call via asyncio.to_thread().

        Args:
            frame: BGR numpy array (from FrameBuffer).

        Returns:
            Metrics dict with all Level 1–5 fields.
            Never raises — returns zeroed metrics on any error.
        """
        t_start = time.monotonic()

        # ── Step 1: True ROI Crop for maximum GPU inference speed ─────────────
        h, w = frame.shape[:2]
        rx1 = max(0, min(int(self._roi.x1), w - 1))
        ry1 = max(0, min(int(self._roi.y1), h - 1))
        rx2 = max(0, min(int(self._roi.x2), w - 1))
        ry2 = max(0, min(int(self._roi.y2), h - 1))

        crop_w = rx2 - rx1
        crop_h = ry2 - ry1

        if crop_w > 10 and crop_h > 10 and (crop_w < w or crop_h < h):
            input_frame = frame[ry1:ry2, rx1:rx2]
            offset_x, offset_y = float(rx1), float(ry1)
        else:
            input_frame = frame
            offset_x, offset_y = 0.0, 0.0

        try:
            tracked: List[TrackedPerson] = self._tracker.update(input_frame)
            if offset_x > 0 or offset_y > 0:
                for p in tracked:
                    p.x1 += offset_x
                    p.x2 += offset_x
                    p.y1 += offset_y
                    p.y2 += offset_y
        except Exception as exc:
            logger.error("QueueAnalyzer tracker error | {e}", e=str(exc))
            tracked = []

        inference_ms = (time.monotonic() - t_start) * 1000.0
        now = time.monotonic()

        # ── Step 2: Filter persons inside ROI ─────────────────────────────────
        in_roi: List[TrackedPerson] = [
            p for p in tracked if self._roi.contains(p.cx, p.cy)
        ]
        count = len(in_roi)

        # ── Step 3: Movement (Level 2) ────────────────────────────────────────
        dt = now - self._prev_time
        if dt < 0.001:
            dt = 0.001  # guard against identical monotonic timestamps

        curr_positions: Dict[int, Tuple[float, float]] = {
            p.track_id: (p.cx, p.cy) for p in in_roi
        }

        if count > 0:
            movements: List[float] = []
            for tid, (cx, cy) in curr_positions.items():
                if tid in self._prev_positions:
                    px, py = self._prev_positions[tid]
                    movements.append(self._forward_progress(cx - px, cy - py))

            if movements:
                self._movement_px = sum(movements) / len(movements)
            else:
                self._movement_px = 0.0

            # ── Step 4: Speed — EMA smoothed (Level 3) ────────────────────────
            raw_speed = self._movement_px / dt
            self._speed_window.append(raw_speed)
            self._speed_px_per_sec = sum(self._speed_window) / len(self._speed_window)

            # ── Step 5: Progress ratio (Level 2 enhancement) ─────────────────
            # Track who is making forward progress (analytics metric only —
            # does NOT influence health classification).
            if movements:
                self._tracked_people = len(movements)
                self._forward_movers = sum(1 for m in movements if m > 0)
                self._progress_ratio = self._forward_movers / self._tracked_people
            else:
                self._tracked_people = 0
                self._forward_movers = 0
                self._progress_ratio = 0.0

            # ── Step 5b: Movement — MEDIAN (majority-vote, not mean) ───────────
            # WHY MEDIAN instead of mean:
            #   [0,0,0,0,0,0,0,0,50,50] → mean=10 (looks MOVING), median=0 (correct BLOCKED)
            # Median is a natural majority-vote: if >50% people are stationary
            # their zeros pull the median to 0, correctly showing blockage.
            # Mean is dominated by the fast movers and inflates the apparent speed.
            self._movement_px = statistics.median(movements) if movements else 0.0

            # ── Step 6: Queue health — asymmetric stabilization (Level 4) ─────
            # Health is PURELY speed-based. No min-people gate needed here
            # because BLOCKED is no longer a health state.
            # (min-people gate remains in Step 7 for the stagnation ALERT)
            raw_health = get_queue_health(self._speed_px_per_sec)

            # Asymmetric stabilization:
            #   DEGRADATION (worse state) → wait stabilization_sec (3s) to confirm
            #   IMPROVEMENT (better state) → wait HEALTH_RECOVERY_SEC (1s) to confirm
            #
            # Without asymmetry, the oscillation trap occurs:
            #   BLOCKED → raw=MOVING (timer 0s) → raw=BLOCKED (timer RESETS)
            #   → raw=MOVING (timer 0s) → never exits BLOCKED
            #
            # With asymmetry, BLOCKED → MOVING only needs 1s → exits quickly.
            if raw_health != self._pending_health:
                self._pending_health = raw_health
                self._pending_since = now

            # Determine required hold time based on improvement vs degradation
            current_rank = HEALTH_ORDER.get(self._queue_health, 0)
            pending_rank = HEALTH_ORDER.get(self._pending_health, 0)
            if pending_rank > current_rank:
                # IMPROVEMENT: adopt quickly
                required_hold = HEALTH_RECOVERY_SEC
            else:
                # DEGRADATION or same: require full confirmation window
                required_hold = self._stabilization_sec

            if (now - self._pending_since) >= required_hold:
                self._queue_health = self._pending_health  # officially adopted

            # ── Step 7: Stagnation / Alert Engine (Level 5) ───────────────────
            # Timer accumulates when:
            #   • speed < ALERT_SPEED_THRESHOLD (2.0 px/s)  — separate from health threshold (10 px/s)
            #   • count >= min_people_for_blockage           — lone person does not trigger alert
            # stagnation_label (OK / BLOCKED / CRITICAL) is the ALERT output.
            if self._speed_px_per_sec < ALERT_SPEED_THRESHOLD and count >= self._min_people_for_blockage:
                if self._stagnation_start is None:
                    self._stagnation_start = now
                self._stagnation_seconds = now - self._stagnation_start
            else:
                self._stagnation_start = None
                self._stagnation_seconds = 0.0
        else:
            # No one in ROI — reset all metrics immediately
            self._movement_px = 0.0
            self._speed_window.clear()
            self._speed_px_per_sec = 0.0
            self._progress_ratio = 0.0
            self._forward_movers = 0
            self._tracked_people = 0
            # EMPTY is exempt from stabilization — take effect immediately
            self._queue_health = "EMPTY"
            self._pending_health = "EMPTY"
            self._pending_since = now
            self._stagnation_start = None
            self._stagnation_seconds = 0.0

        # Update position history and timestamp
        # (direction stored for reference in metrics)
        self._prev_positions = curr_positions
        self._prev_time = now

        # ── Step 7: Build output ──────────────────────────────────────────────
        queue_status = get_queue_status(count, self._low_max, self._medium_max)
        stagnation_label = get_stagnation_label(self._stagnation_seconds)

        return {
            # Level 1
            "people_inside_queue": count,
            "queue_length": count,
            "queue_status": queue_status,
            # Level 2 — movement (median-based) + progress analytics
            "movement_px": round(self._movement_px, 2),
            "forward_movers": self._forward_movers,
            "tracked_people": self._tracked_people,
            "progress_ratio": round(self._progress_ratio, 2),
            # Level 3
            "speed_px_per_sec": round(self._speed_px_per_sec, 2),
            # Level 4
            "queue_health": self._queue_health,
            # pending_health is internal only — kept for stabilization logic,
            # not exposed in API (remove clutter from production responses).
            "_pending_health": self._pending_health,  # internal/debug
            # Level 5
            "stagnation_seconds": round(self._stagnation_seconds, 1),
            "stagnation_label": stagnation_label,
            # Meta
            "queue_direction": self._direction,
            "inference_ms": inference_ms,
        }
