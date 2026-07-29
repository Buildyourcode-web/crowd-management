"""EventRepository — unified event log operations."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import EventSeverity, EventType
from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Event, session)

    async def get_recent(
        self, limit: int = 100, severity: Optional[EventSeverity] = None
    ) -> List[Event]:
        stmt = select(Event).order_by(Event.occurred_at.desc())
        if severity:
            stmt = stmt.where(Event.severity == severity)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(
        self, event_type: EventType, limit: int = 50
    ) -> List[Event]:
        result = await self.session.execute(
            select(Event)
            .where(Event.event_type == event_type)
            .order_by(Event.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def acknowledge_event(
        self, event: Event, acknowledged_by: str
    ) -> Event:
        event.is_acknowledged = True
        event.acknowledged_by = acknowledged_by
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def count_unacknowledged(self) -> int:
        return await self.count(Event.is_acknowledged == False)  # noqa: E712
