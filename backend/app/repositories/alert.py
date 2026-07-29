"""AlertRepository — all alert database operations."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import AlertSeverity, AlertStatus
from app.models.alert import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Alert, session)

    async def get_open_alerts(
        self, limit: int = 50
    ) -> List[Alert]:
        result = await self.session.execute(
            select(Alert)
            .where(Alert.status == AlertStatus.OPEN)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_severity(
        self, severity: AlertSeverity, limit: int = 50
    ) -> List[Alert]:
        result = await self.session.execute(
            select(Alert)
            .where(Alert.severity == severity)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def acknowledge_alert(
        self, alert: Alert, acknowledged_by: str
    ) -> Alert:
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now(timezone.utc)
        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def resolve_alert(
        self,
        alert: Alert,
        resolved_by: str,
        resolution_note: Optional[str] = None,
    ) -> Alert:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_by = resolved_by
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_note = resolution_note
        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def count_open(self) -> int:
        return await self.count(Alert.status == AlertStatus.OPEN)
