"""Person counting pipeline — Phase 4.

Implements Entry/Exit counting via ByteTrack + virtual counting line.
"""
from app.person_counter.worker import person_counter_manager, PersonCounterManager
from app.person_counter.tracker import PersonTracker, TrackedPerson
from app.person_counter.roi import CountingLine
from app.person_counter.counter import PersonCounter
from app.person_counter.schemas import CountingLineConfig, PersonCountStatus

__all__ = [
    "person_counter_manager",
    "PersonCounterManager",
    "PersonTracker",
    "TrackedPerson",
    "CountingLine",
    "PersonCounter",
    "CountingLineConfig",
    "PersonCountStatus",
]
