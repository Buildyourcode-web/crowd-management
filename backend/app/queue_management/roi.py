"""
Queue ROI — Rectangle Region of Interest (Task 1).

═══════════════════════════════════════════════════════════════════════
What is a Queue ROI?
═══════════════════════════════════════════════════════════════════════

A Queue ROI is an axis-aligned rectangle drawn on the camera frame.
Only persons whose centroid (centre of bounding box) falls inside this
rectangle are counted as part of the queue.

Persons outside the rectangle (e.g. walking past, sitting nearby)
are completely ignored — they never affect the queue count.

═══════════════════════════════════════════════════════════════════════
Coordinate system
═══════════════════════════════════════════════════════════════════════

    (0,0) ── x increases ──▶  (width, 0)
      │
      │ y increases
      ▼
    (0, height)              (width, height)

Origin is the TOP-LEFT corner (standard OpenCV / image convention).

═══════════════════════════════════════════════════════════════════════
Rectangle
═══════════════════════════════════════════════════════════════════════

    (x1, y1) ──────────── (x2, y1)
        │                      │
        │     Queue Area        │
        │                      │
    (x1, y2) ──────────── (x2, y2)

A person's centroid (cx, cy) is inside if:
    x1 ≤ cx ≤ x2  AND  y1 ≤ cy ≤ y2

═══════════════════════════════════════════════════════════════════════
Normalisation
═══════════════════════════════════════════════════════════════════════

__post_init__ ensures x1 ≤ x2 and y1 ≤ y2 regardless of input order.
This makes the ROI robust to accidentally swapped corners.
"""
from dataclasses import dataclass


@dataclass
class QueueROI:
    """
    Axis-aligned rectangle ROI for one camera.

    One ROI per camera — no polygons, no multiple regions.

    Args:
        x1, y1: top-left corner (pixels)
        x2, y2: bottom-right corner (pixels)
    """

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        """Normalise corners so x1 ≤ x2 and y1 ≤ y2 always hold."""
        self.x1, self.x2 = min(self.x1, self.x2), max(self.x1, self.x2)
        self.y1, self.y2 = min(self.y1, self.y2), max(self.y1, self.y2)

    # ── Spatial test ──────────────────────────────────────────────────────────

    def contains(self, cx: float, cy: float) -> bool:
        """
        Return True if the point (cx, cy) is inside or on the boundary.

        Args:
            cx: horizontal centroid of a detected bounding box.
            cy: vertical centroid of a detected bounding box.
        """
        return self.x1 <= cx <= self.x2 and self.y1 <= cy <= self.y2

    # ── Utility ───────────────────────────────────────────────────────────────

    @property
    def area(self) -> float:
        """Rectangle area in pixels²."""
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    def __repr__(self) -> str:
        return (
            f"QueueROI(({self.x1:.0f},{self.y1:.0f})"
            f"→({self.x2:.0f},{self.y2:.0f}), area={self.area:.0f}px²)"
        )
