"""
Zone — Pure-geometry rectangle class (Task 2).

═══════════════════════════════════════════════════════════════════════
Zone overview
═══════════════════════════════════════════════════════════════════════

A Zone is an axis-aligned rectangle drawn on a camera frame.
It has NO OpenCV or numpy dependency — pure Python geometry only.

When ZoneAnalyzer processes a frame it calls contains_point(cx, cy)
for every detected person to decide which zone that person belongs to.

═══════════════════════════════════════════════════════════════════════
Coordinate system
═══════════════════════════════════════════════════════════════════════

    (0,0) ── x increases ──▶  (frame_width, 0)
      │
      │ y increases
      ▼
    (0, frame_height)

Origin is the TOP-LEFT corner (standard OpenCV / image convention).

    (x1, y1) ──────────────────────── (x2, y1)
        │                                 │
        │            Zone Area            │
        │                                 │
    (x1, y2) ──────────────────────── (x2, y2)

═══════════════════════════════════════════════════════════════════════
Normalisation
═══════════════════════════════════════════════════════════════════════

__post_init__ automatically ensures x1 ≤ x2 and y1 ≤ y2 regardless of
the input order. This makes Zone robust to swapped corners.

═══════════════════════════════════════════════════════════════════════
Density calculation (Task 4, 5)
═══════════════════════════════════════════════════════════════════════

    density = people_count / (zone.area() / 1000.0)

Unit: "people per 1000 pixel²"
This normalisation produces human-readable float values (e.g. 0.09)
for typical temple camera zones (100k–500k px²).

Density is reported as a metric but the zone STATUS thresholds are
applied to people_count, not density.

═══════════════════════════════════════════════════════════════════════
First-match rule for overlapping zones (Task 14)
═══════════════════════════════════════════════════════════════════════

If two zones overlap, a person is assigned to the FIRST zone in the
list whose contains_point() returns True. The analyzer stops checking
after the first match — no double counting.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Zone:
    """
    Axis-aligned rectangle zone for one camera.

    Args:
        zone_id:   Unique string identifier (e.g. "A", "entrance").
        zone_name: Human-readable name (e.g. "Temple Entrance").
        x1, y1:   Top-left corner in pixels.
        x2, y2:   Bottom-right corner in pixels.
    """

    zone_id: str
    zone_name: str
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        """Normalise corners so x1 ≤ x2 and y1 ≤ y2 always hold."""
        self.x1, self.x2 = min(self.x1, self.x2), max(self.x1, self.x2)
        self.y1, self.y2 = min(self.y1, self.y2), max(self.y1, self.y2)

    # ── Spatial methods (Task 2) ──────────────────────────────────────────────

    def contains_point(self, x: float, y: float) -> bool:
        """
        Return True if (x, y) is inside or on the boundary of this zone.

        Used by ZoneAnalyzer to assign each detected person to a zone.
        Boundary inclusion (≤) means a centroid exactly on the edge counts.
        """
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def center(self) -> Tuple[float, float]:
        """Return the (cx, cy) centre point of the rectangle."""
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def area(self) -> float:
        """Return the rectangle area in pixel²."""
        return self.width() * self.height()

    def width(self) -> float:
        """Return the rectangle width in pixels (x2 − x1)."""
        return self.x2 - self.x1

    def height(self) -> float:
        """Return the rectangle height in pixels (y2 − y1)."""
        return self.y2 - self.y1

    # ── Utilities ─────────────────────────────────────────────────────────────

    def overlaps(self, other: "Zone") -> bool:
        """
        Return True if this zone overlaps with another zone.

        Used by ZoneAnalyzer to log a warning when overlapping zones are
        configured (overlap is allowed but logged — Task 14).
        """
        return (
            self.x1 < other.x2 and self.x2 > other.x1
            and self.y1 < other.y2 and self.y2 > other.y1
        )

    def __repr__(self) -> str:
        return (
            f"Zone(id={self.zone_id!r}, name={self.zone_name!r}, "
            f"({self.x1:.0f},{self.y1:.0f})→({self.x2:.0f},{self.y2:.0f}), "
            f"area={self.area():.0f}px²)"
        )
