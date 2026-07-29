"""Health check response schemas."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: str  # 'healthy' | 'unhealthy' | 'degraded'
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: Optional[ComponentHealth] = None
    redis: Optional[ComponentHealth] = None
    application: Optional[ComponentHealth] = None


class ApplicationInfo(BaseModel):
    name: str
    version: str
    environment: str
    uptime_seconds: float
    debug: bool


class MetricsResponse(BaseModel):
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    uptime_seconds: float
    database: ComponentHealth
    redis: ComponentHealth
    active_websocket_connections: int


class VersionResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    api_prefix: str
    debug: bool
    build_timestamp: Optional[str] = None
