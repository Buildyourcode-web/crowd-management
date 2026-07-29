"""Health Service — checks DB, Redis, and system metrics."""
import time
from datetime import datetime, timezone
from typing import Optional

import psutil
from loguru import logger

from app.common.exceptions import DatabaseConnectionException, RedisConnectionException
from app.config.settings import settings
from app.database.connection import check_db_health
from app.schemas.health import (
    ApplicationInfo,
    ComponentHealth,
    HealthResponse,
    MetricsResponse,
    VersionResponse,
)
from app.utils.redis_manager import redis_manager
from app.websocket.manager import ws_manager

# Track application start time
_start_time: float = time.monotonic()


class HealthService:
    """Provides system health and metrics information."""

    async def get_overall_health(self) -> HealthResponse:
        """Aggregate health check across all components."""
        db_health = await self._check_database()
        redis_health = await self._check_redis()

        overall = "healthy"
        if db_health.status != "healthy" or redis_health.status != "healthy":
            overall = "degraded"

        return HealthResponse(
            status=overall,
            timestamp=datetime.now(timezone.utc),
            database=db_health,
            redis=redis_health,
        )

    async def get_database_health(self) -> ComponentHealth:
        return await self._check_database()

    async def get_redis_health(self) -> ComponentHealth:
        return await self._check_redis()

    def get_application_info(self) -> ApplicationInfo:
        return ApplicationInfo(
            name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            uptime_seconds=round(time.monotonic() - _start_time, 2),
            debug=settings.DEBUG,
        )

    def get_version(self) -> VersionResponse:
        return VersionResponse(
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            api_prefix=settings.API_V1_PREFIX,
            debug=settings.DEBUG,
        )

    async def get_metrics(self) -> MetricsResponse:
        """Collect system resource metrics."""
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime = round(time.monotonic() - _start_time, 2)

        db_health = await self._check_database()
        redis_health = await self._check_redis()

        return MetricsResponse(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_used_mb=round(mem.used / 1024 / 1024, 2),
            memory_total_mb=round(mem.total / 1024 / 1024, 2),
            disk_percent=disk.percent,
            uptime_seconds=uptime,
            database=db_health,
            redis=redis_health,
            active_websocket_connections=ws_manager.total_connections,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _check_database(self) -> ComponentHealth:
        try:
            result = await check_db_health()
            return ComponentHealth(
                status=result["status"],
                latency_ms=result["latency_ms"],
            )
        except DatabaseConnectionException as exc:
            return ComponentHealth(status="unhealthy", detail=exc.message)
        except Exception as exc:
            return ComponentHealth(status="unhealthy", detail=str(exc))

    async def _check_redis(self) -> ComponentHealth:
        try:
            result = await redis_manager.ping()
            return ComponentHealth(
                status=result["status"],
                latency_ms=result["latency_ms"],
            )
        except RedisConnectionException as exc:
            return ComponentHealth(status="unhealthy", detail=exc.message)
        except Exception as exc:
            return ComponentHealth(status="unhealthy", detail=str(exc))


health_service = HealthService()
