"""
PersonCounter — Entry / Exit / Occupancy counters (Task 5).

Maintains three integer values for ONE camera:

    entry_count       — cumulative persons who entered (only increases)
    exit_count        — cumulative persons who exited  (only increases)
    current_occupancy — max(0, entry_count − exit_count)

═══════════════════════════════════════════════════════════════════════
Occupancy formula
═══════════════════════════════════════════════════════════════════════

    current_occupancy = max(0, entry_count − exit_count)

The max(0, ...) clamp prevents negative occupancy caused by:
  • Exits counted before the initial entry (person enters from outside
    the camera frame)
  • Sensor drift or missed detections

═══════════════════════════════════════════════════════════════════════
Thread-safety
═══════════════════════════════════════════════════════════════════════

The counter is accessed exclusively from one PersonCounterWorker asyncio.Task.
Since asyncio is single-threaded (cooperative), no locks are needed.
"""


class PersonCounter:
    """
    Simple cumulative counter for one camera stream.

    Caller contract: always accessed from a single asyncio Task.
    """

    __slots__ = ("_entry", "_exit")

    def __init__(self) -> None:
        self._entry: int = 0
        self._exit: int = 0

    # ── Mutators ──────────────────────────────────────────────────────────────

    def add_entry(self) -> None:
        """Record one person entering."""
        self._entry += 1

    def add_exit(self) -> None:
        """Record one person exiting."""
        self._exit += 1

    def reset(self) -> None:
        """
        Reset all counters to zero.
        Useful for shift changes or calibration — not called automatically.
        """
        self._entry = 0
        self._exit = 0

    # ── Read-only properties ──────────────────────────────────────────────────

    @property
    def entry_count(self) -> int:
        """Cumulative entry count (never decreases)."""
        return self._entry

    @property
    def exit_count(self) -> int:
        """Cumulative exit count (never decreases)."""
        return self._exit

    @property
    def current_occupancy(self) -> int:
        """
        Estimated number of persons currently inside.
        Clamped to 0 — never returns a negative value.
        """
        return max(0, self._entry - self._exit)

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """
        Return all three values as a plain dict.
        Safe to call from any context — pure read with no side effects.
        """
        return {
            "entry_count": self._entry,
            "exit_count": self._exit,
            "current_occupancy": self.current_occupancy,
        }
