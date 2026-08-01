"""
Dashboard API — notification feed used by the React frontend.

The frontend polls GET /api/v1/dashboard/notifications?filter=all every 5 s.
This endpoint aggregates recent alerts into the notification shape that the
frontend's useNotifications hook expects:

    {
        "notifications": [...],
        "unread_count": 3
    }

When the database is unavailable (DEGRADED mode) it returns an empty list
gracefully instead of raising a 500.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.database.connection import get_db
from app.models.alert import Alert

router = APIRouter(tags=["Dashboard"])


# ─── Helper ──────────────────────────────────────────────────────────────────

def _alert_to_notification(alert: Alert) -> dict:
    """Convert an Alert ORM row into the frontend notification shape."""
    return {
        "id": str(alert.id),
        "type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
        "title": alert.title,
        "message": alert.message,
        "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
        "is_read": alert.acknowledged_at is not None,
        "camera_id": str(alert.camera_id) if alert.camera_id else None,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


# ─── GET /dashboard/notifications ────────────────────────────────────────────

@router.get(
    "/dashboard/notifications",
    response_model=ApiResponse,
    summary="Get notification feed for dashboard",
)
async def get_dashboard_notifications(
    filter: Optional[str] = Query(default="all", description="Filter: all | unread | critical"),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Aggregated notification feed sourced from the alerts table.

    Returns an empty list gracefully when the database is unavailable
    (DEGRADED mode) so the frontend does not display error states.

    **Query params**:
    - `filter` — `all` (default) | `unread` | `critical`
    - `limit` — max results (default 50, max 200)
    """
    try:
        stmt = select(Alert).order_by(desc(Alert.created_at)).limit(limit)

        # Apply filter
        if filter == "unread":
            stmt = stmt.where(Alert.acknowledged_at.is_(None))
        elif filter == "critical":
            from app.common.enums import AlertSeverity
            stmt = stmt.where(Alert.severity == AlertSeverity.CRITICAL)

        result = await db.execute(stmt)
        alerts = result.scalars().all()

        notifications = [_alert_to_notification(a) for a in alerts]
        unread_count = sum(1 for n in notifications if not n["is_read"])

        return ApiResponse.ok(
            data={
                "notifications": notifications,
                "unread_count": unread_count,
            },
            message="Notifications retrieved",
        )

    except Exception as exc:
        # DB unavailable (DEGRADED mode) — return empty list, not a 500
        logger.debug("Dashboard notifications: DB unavailable, returning empty | err={e}", e=str(exc))
        return ApiResponse.ok(
            data={
                "notifications": [],
                "unread_count": 0,
            },
            message="Notifications unavailable (database offline)",
        )


# ─── POST /dashboard/notifications/{id}/read ─────────────────────────────────

@router.post(
    "/dashboard/notifications/{notification_id}/read",
    response_model=ApiResponse,
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Mark a single alert/notification as acknowledged (read)."""
    try:
        result = await db.execute(select(Alert).where(Alert.id == notification_id))
        alert = result.scalar_one_or_none()
        if alert and not alert.acknowledged_at:
            alert.acknowledged_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception as exc:
        logger.debug("Mark notification read failed | err={e}", e=str(exc))

    return ApiResponse.ok(data={"id": str(notification_id), "is_read": True}, message="Marked as read")


# ─── POST /dashboard/notifications/read-all ──────────────────────────────────

@router.post(
    "/dashboard/notifications/read-all",
    response_model=ApiResponse,
    summary="Mark all notifications as read",
)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Mark all unread alerts as acknowledged."""
    try:
        from sqlalchemy import update
        stmt = (
            update(Alert)
            .where(Alert.acknowledged_at.is_(None))
            .values(acknowledged_at=datetime.now(timezone.utc))
        )
        await db.execute(stmt)
        await db.commit()
    except Exception as exc:
        logger.debug("Mark all notifications read failed | err={e}", e=str(exc))

    return ApiResponse.ok(data={"marked_all_read": True}, message="All notifications marked as read")
