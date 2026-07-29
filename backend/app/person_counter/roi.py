"""
ROI — Virtual Counting Line (Task 3 + Task 4).

A single straight line drawn on the camera frame.
When a tracked person's bottom-centre crosses this line, an entry or
exit event fires.

═══════════════════════════════════════════════════════════════════════
Coordinate system
═══════════════════════════════════════════════════════════════════════

    (0,0) ── x increases ──▶
      │
      │ y increases
      ▼

Origin is the TOP-LEFT corner (standard OpenCV / image convention).

═══════════════════════════════════════════════════════════════════════
Line orientation detection
═══════════════════════════════════════════════════════════════════════

    Horizontal line: |dx| >= |dy|   → drawn left-to-right
    Vertical line:   |dy|  > |dx|   → drawn top-to-bottom

═══════════════════════════════════════════════════════════════════════
Entry / Exit convention (Task 4)
═══════════════════════════════════════════════════════════════════════

    Horizontal line (left → right):
        Top   → Bottom  =  Entry   (person moves downward, y increases)
        Bottom → Top    =  Exit

    Vertical line (top → bottom):
        Left  → Right   =  Entry   (person moves rightward, x increases)
        Right → Left    =  Exit

═══════════════════════════════════════════════════════════════════════
Math — which side of a line is a point on?
═══════════════════════════════════════════════════════════════════════

Given directed line from A=(start_x, start_y) to B=(end_x, end_y),
and point P=(x, y):

    cross = (B-A) × (P-A)
           = dx*(py) − dy*(px)
    where dx = end_x - start_x
          dy = end_y - start_y
          px = x - start_x
          py = y - start_y

    cross > 0  → point is on the LEFT  of the directed line (side +1)
    cross < 0  → point is on the RIGHT of the directed line (side -1)

Side assignment per orientation:

    Horizontal line (A→B goes right, dy≈0):
        cross ≈ dx * py
        py < 0 (above line): cross < 0 → side = -1  (ABOVE)
        py > 0 (below line): cross > 0 → side = +1  (BELOW)
        Crossing: side -1 → +1 = top to bottom = ENTRY ✓

    Vertical line (A→B goes down, dx≈0):
        cross ≈ -dy * px
        px < 0 (left of line): cross > 0 → side = +1  (LEFT)
        px > 0 (right of line): cross < 0 → side = -1  (RIGHT)
        Crossing: side +1 → -1 = left to right = ENTRY ✓

═══════════════════════════════════════════════════════════════════════
Anti-double-counting guarantee (Task 4)
═══════════════════════════════════════════════════════════════════════

Each crossing is detected by a SIGN CHANGE in the cross-product side.
A single trajectory produces at most one sign change per crossing.
The worker stores the previous centroid per track_id and only fires when
the side actually flips — so one physical crossing = one count event.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class CountingLine:
    """
    A directed counting line from (start_x, start_y) → (end_x, end_y).

    Draw horizontal lines left-to-right.
    Draw vertical lines top-to-bottom.
    """

    start_x: float
    start_y: float
    end_x: float
    end_y: float

    # ── Geometry helpers ──────────────────────────────────────────────────────

    @property
    def is_horizontal(self) -> bool:
        """True when the line spans more width than height."""
        return abs(self.end_x - self.start_x) >= abs(self.end_y - self.start_y)

    def _side(self, x: float, y: float) -> int:
        """
        Return which side of the directed line the point (x, y) is on.

        Uses the Z-component of the 2D cross product
        (end−start) × (point−start).

        Returns:
             +1  — positive side  (above for horizontal, left for vertical)
             -1  — negative side  (below for horizontal, right for vertical)
              0  — point is exactly on the line
        """
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        px = x - self.start_x
        py = y - self.start_y
        cross = dx * py - dy * px
        if cross > 0:
            return 1
        if cross < 0:
            return -1
        return 0

    # ── Crossing detection ────────────────────────────────────────────────────

    def check_crossing(
        self,
        prev_x: float,
        prev_y: float,
        curr_x: float,
        curr_y: float,
    ) -> Optional[str]:
        """
        Detect whether a person crossed the line between two frames.

        Args:
            prev_x, prev_y: person centroid in the **previous** frame.
            curr_x, curr_y: person centroid in the **current** frame.

        Returns:
            "entry"  — crossed in the configured entry direction.
            "exit"   — crossed in the configured exit direction.
            None     — no crossing (same side, or on the line).

        Anti-double-count: returns non-None only when the side CHANGES.
        The worker stores prev position per track_id, so one physical
        crossing produces exactly one "entry" or "exit" event.
        """
        prev_side = self._side(prev_x, prev_y)
        curr_side = self._side(curr_x, curr_y)

        # No crossing: same side or one point lies exactly on the line
        if prev_side == 0 or curr_side == 0 or prev_side == curr_side:
            return None

        if self.is_horizontal:
            # ── Segment bounds check ──────────────────────────────────────────
            # Only fire if the person's current X is within the drawn segment.
            # Without this, the infinite-line formula would count anyone crossing
            # the Y threshold regardless of their X position.
            x_min = min(self.start_x, self.end_x)
            x_max = max(self.start_x, self.end_x)
            if not (x_min <= curr_x <= x_max):
                return None
            # Horizontal: side -1 = above, side +1 = below
            # Top → Bottom (−1 → +1) = ENTRY
            return "entry" if (prev_side < 0 and curr_side > 0) else "exit"
        else:
            # ── Segment bounds check ──────────────────────────────────────────
            # Only fire if the person's current Y is within the drawn segment.
            y_min = min(self.start_y, self.end_y)
            y_max = max(self.start_y, self.end_y)
            if not (y_min <= curr_y <= y_max):
                return None
            # Vertical: side +1 = left, side -1 = right
            # Left → Right (+1 → −1) = ENTRY
            return "entry" if (prev_side > 0 and curr_side < 0) else "exit"


@dataclass
class TriggerZone:
    """
    Rectangular trigger zone for counting persons.

    HOW IT WORKS:
    ─────────────
    Instead of a thin line (which causes micro-crossing issues), a rectangular
    zone is drawn on the frame.

    When a person's centroid ENTERS this rectangle for the first time,
    they are counted as an ENTRY. While they remain inside the zone, or
    after they exit, they are NEVER re-counted (tracked by track_id).

    This eliminates:
      ✓ Back-and-forth line oscillation double-counts
      ✓ Ambiguity about "when" the line was crossed
      ✓ Micro-movement near the trigger point

    PLACEMENT:
    ──────────
    Place the zone at the actual door/gate threshold:
    - For a door camera: zone spans the width of the doorway at floor level
    - Persons walk through the zone from outside → inside (or vice versa)
    - Zone height = ~30% of frame height for a clear trigger window

    COORDINATES:
    ────────────
    (x1, y1) = top-left corner
    (x2, y2) = bottom-right corner
    All in absolute pixel coords of the camera resolution.
    """

    x1: float   # left edge
    y1: float   # top edge
    x2: float   # right edge
    y2: float   # bottom edge

    def contains(self, cx: float, cy: float) -> bool:
        """Return True if point (cx, cy) is inside the zone rectangle."""
        return self.x1 <= cx <= self.x2 and self.y1 <= cy <= self.y2

    @classmethod
    def from_center(
        cls,
        cx: float,
        cy: float,
        width: float,
        height: float,
    ) -> "TriggerZone":
        """Create zone from center point + dimensions."""
        return cls(
            x1=cx - width / 2,
            y1=cy - height / 2,
            x2=cx + width / 2,
            y2=cy + height / 2,
        )

    @classmethod
    def for_horizontal_band(
        cls,
        frame_width: float,
        y_center: float,
        band_height: float = 120.0,
    ) -> "TriggerZone":
        """
        Create a full-width horizontal band zone centered at y_center.
        Use this to replace a horizontal counting line with a wider trigger strip.
        """
        return cls(
            x1=0,
            y1=y_center - band_height / 2,
            x2=frame_width,
            y2=y_center + band_height / 2,
        )
