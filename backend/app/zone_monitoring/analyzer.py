"""
ZoneAnalyzer — Frame-level multi-zone analysis (Tasks 3, 4, 5, 6, 16).

═══════════════════════════════════════════════════════════════════════
Zone Analyzer overview
═══════════════════════════════════════════════════════════════════════

Given one camera frame and a list of configured zones, ZoneAnalyzer:

    1.  Calls detector.detect(frame) — shared Detector singleton
        (never reloads YOLO, never creates a new model instance)
    2.  Iterates all detections — keeps only class "person" (COCO 0)
    3.  For each person: computes centroid (cx, cy) of bounding box
    4.  Checks zones in order — assigns person to FIRST matching zone
        (stops after first match → no double-counting)
    5.  Persons outside all zones are ignored
    6.  Computes per-zone metrics: people_count, density, status
    7.  Returns the full result dict (Task 6)

═══════════════════════════════════════════════════════════════════════
Density calculation (Task 5)
═══════════════════════════════════════════════════════════════════════

    density = people_count / (zone.area() / 1000.0)

Unit: "people per 1000 pixel²"
Normalising by 1000 px² gives human-readable floats for typical
temple camera zones (100k–500k px²). Example: 18 people in a
202,800 px² zone → density ≈ 0.089.

Density is a separate metric — it is NOT used for status thresholds.

═══════════════════════════════════════════════════════════════════════
Zone status thresholds (Task 5)
═══════════════════════════════════════════════════════════════════════

Thresholds are applied to people_count (not density):

    0            → EMPTY
    1 – low_max  → LOW       default low_max    = 10
    11 – med_max → MEDIUM    default medium_max = 25
    26 – high_max→ HIGH      default high_max   = 40
    41+          → CRITICAL

All thresholds are configurable per-camera when starting the worker.

═══════════════════════════════════════════════════════════════════════
Overlapping zones (Task 14)
═══════════════════════════════════════════════════════════════════════

Overlapping zones are allowed but warned about at startup.
When a person's centroid falls in two zones, the zone that appears
FIRST in the configured list wins. This is deterministic and ensures
each person is counted at most once across all zones.

═══════════════════════════════════════════════════════════════════════
Result schema (Task 6)
═══════════════════════════════════════════════════════════════════════

analyze() returns:
{
    "camera_id":          "...",
    "timestamp":          "2026-07-25T00:00:00+00:00",
    "processing_time_ms": 46.3,
    "zones": [
        {
            "zone_id":      "A",
            "zone_name":    "Temple Entrance",
            "people_count": 18,
            "density":      0.089,
            "status":       "MEDIUM"
        },
        ...
    ]
}
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
from loguru import logger

from app.ai.detector import detector
from app.zone_monitoring.zone import Zone

# COCO class index for "person"
PERSON_CLASS_ID: int = 0

# ── Configurable thresholds ────────────────────────────────────────────────────
DEFAULT_LOW_MAX: int = 10    # 1–10 persons   → LOW
DEFAULT_MEDIUM_MAX: int = 25 # 11–25 persons  → MEDIUM
DEFAULT_HIGH_MAX: int = 40   # 26–40 persons  → HIGH
                             # 41+ persons    → CRITICAL


def get_zone_status(
    count: int,
    low_max: int = DEFAULT_LOW_MAX,
    medium_max: int = DEFAULT_MEDIUM_MAX,
    high_max: int = DEFAULT_HIGH_MAX,
) -> str:
    """
    Map a person count to a zone status string.

    Args:
        count:      Number of persons inside the zone (>= 0).
        low_max:    Upper bound of LOW band (inclusive).   Default 10.
        medium_max: Upper bound of MEDIUM band (inclusive). Default 25.
        high_max:   Upper bound of HIGH band (inclusive).   Default 40.

    Returns:
        "EMPTY"    count == 0
        "LOW"      1 ≤ count ≤ low_max
        "MEDIUM"   low_max < count ≤ medium_max
        "HIGH"     medium_max < count ≤ high_max
        "CRITICAL" count > high_max
    """
    if count == 0:
        return "EMPTY"
    if count <= low_max:
        return "LOW"
    if count <= medium_max:
        return "MEDIUM"
    if count <= high_max:
        return "HIGH"
    return "CRITICAL"


class ZoneAnalyzer:
    """
    Per-camera zone analysis engine.

    One ZoneAnalyzer is created per ZoneWorker.
    It holds the camera's zone list and threshold configuration.
    ZoneAnalyzer is stateless — safe to call analyze() repeatedly.

    Usage (synchronous — call via asyncio.to_thread from the worker):
        analyzer = ZoneAnalyzer(camera_id, zones)
        result   = analyzer.analyze(frame)
    """

    def __init__(
        self,
        camera_id: str,
        zones: List[Zone],
        low_max: int = DEFAULT_LOW_MAX,
        medium_max: int = DEFAULT_MEDIUM_MAX,
        high_max: int = DEFAULT_HIGH_MAX,
    ) -> None:
        self._camera_id = camera_id
        self._zones = zones
        self._low_max = low_max
        self._medium_max = medium_max
        self._high_max = high_max
        self._check_overlaps()

    # ── Overlap warning ───────────────────────────────────────────────────────

    def _check_overlaps(self) -> None:
        """Log a warning for every pair of overlapping zones (Task 14)."""
        for i, za in enumerate(self._zones):
            for j, zb in enumerate(self._zones):
                if i >= j:
                    continue
                if za.overlaps(zb):
                    logger.warning(
                        "ZoneAnalyzer | camera={cid} | "
                        "zones '{a}' and '{b}' overlap — "
                        "person in overlap area will be assigned to '{a}' (first-match rule)",
                        cid=self._camera_id,
                        a=za.zone_id,
                        b=zb.zone_id,
                    )

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect persons in frame and compute metrics for every zone.

        Pipeline:
            detector.detect(frame)
            → filter class == person
            → centroid per person
            → first-match zone assignment
            → people_count per zone
            → density + status per zone

        Args:
            frame: BGR numpy array from the camera's FrameBuffer.

        Returns:
            Full result dict (Task 6 schema).
            Returns zeroed metrics on any error — never raises.
        """
        t_start = time.monotonic()
        now = datetime.now(timezone.utc).isoformat()

        # ── Step 1: Detection via shared Detector singleton ───────────────────
        results = detector.detect(frame)
        processing_ms = (time.monotonic() - t_start) * 1000.0

        # Initialise per-zone person counts
        zone_counts: Dict[str, int] = {z.zone_id: 0 for z in self._zones}

        if results is not None and results and results[0].boxes is not None:
            boxes = results[0].boxes
            try:
                class_ids = boxes.cls.cpu().numpy().astype(int).tolist()
                xyxy = boxes.xyxy.cpu().numpy()
            except Exception as exc:
                logger.error(
                    "ZoneAnalyzer box parse error | camera={cid} | {err}",
                    cid=self._camera_id,
                    err=str(exc),
                )
                class_ids, xyxy = [], []

            # ── Step 2: Assign each person to first matching zone ─────────────
            for box, cls_id in zip(xyxy, class_ids):
                if cls_id != PERSON_CLASS_ID:
                    continue  # Ignore non-person detections

                cx = (float(box[0]) + float(box[2])) / 2.0
                cy = (float(box[1]) + float(box[3])) / 2.0

                # First-match rule: stop after assigning to one zone
                for zone in self._zones:
                    if zone.contains_point(cx, cy):
                        zone_counts[zone.zone_id] += 1
                        break  # Person belongs to only one zone (Task 3)

        # ── Step 3: Compute per-zone metrics ──────────────────────────────────
        zone_results = []
        for zone in self._zones:
            count = zone_counts[zone.zone_id]
            area = zone.area()

            # density = people per 1000 pixel² (safe even for tiny zones)
            density = round(count / (area / 1000.0), 4) if area > 0 else 0.0

            status = get_zone_status(
                count, self._low_max, self._medium_max, self._high_max
            )

            zone_results.append({
                "zone_id":      zone.zone_id,
                "zone_name":    zone.zone_name,
                "people_count": count,
                "density":      density,
                "status":       status,
            })

        return {
            "camera_id":          self._camera_id,
            "timestamp":          now,
            "processing_time_ms": round(processing_ms, 2),
            "zones":              zone_results,
        }
