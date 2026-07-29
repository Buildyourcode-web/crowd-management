"""Alert Service — manages alert lifecycle."""
from typing import List, Optional
import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import AlertSeverity
from app.common.exceptions import AlertNotFoundException
from app.models.alert import Alert
from app.repositories.alert import AlertRepository
from app.schemas.alert import AlertCreate, AlertAcknowledge, AlertResolve


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AlertRepository(session)

    async def create_alert(self, data: AlertCreate) -> Alert:
        alert = Alert(
            title=data.title,
            message=data.message,
            alert_type=data.alert_type,
            severity=data.severity,
            camera_id=data.camera_id,
            zone_id=data.zone_id,
            queue_id=data.queue_id,
            extra_data=data.extra_data,
        )
        alert = await self._repo.create(alert)
        logger.info(
            "Alert created | id={id} | type={t} | severity={s}",
            id=alert.id,
            t=alert.alert_type,
            s=alert.severity,
        )
        return alert

    async def get_alert(self, alert_id: uuid.UUID) -> Alert:
        alert = await self._repo.get_by_id(alert_id)
        if not alert:
            raise AlertNotFoundException(alert_id)
        return alert

    async def list_alerts(
        self,
        skip: int = 0,
        limit: int = 20,
        open_only: bool = False,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Alert]:
        if open_only:
            return await self._repo.get_open_alerts(limit=limit)
        if severity:
            return await self._repo.get_by_severity(severity=severity, limit=limit)
        return await self._repo.get_all(skip=skip, limit=limit)

    async def acknowledge_alert(
        self, alert_id: uuid.UUID, data: AlertAcknowledge
    ) -> Alert:
        alert = await self.get_alert(alert_id)
        alert = await self._repo.acknowledge_alert(alert, data.acknowledged_by)
        logger.info("Alert acknowledged | id={id} | by={by}", id=alert_id, by=data.acknowledged_by)
        return alert

    async def resolve_alert(
        self, alert_id: uuid.UUID, data: AlertResolve
    ) -> Alert:
        alert = await self.get_alert(alert_id)
        alert = await self._repo.resolve_alert(
            alert, data.resolved_by, data.resolution_note
        )
        logger.info("Alert resolved | id={id} | by={by}", id=alert_id, by=data.resolved_by)
        return alert

    async def count_open_alerts(self) -> int:
        return await self._repo.count_open()
