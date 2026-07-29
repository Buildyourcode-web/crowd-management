"""System metrics API endpoint."""
from fastapi import APIRouter

from app.common.response import ApiResponse
from app.services.health.health_service import health_service

router = APIRouter()


@router.get(
    "",
    summary="System metrics",
    description="Returns CPU, memory, disk, Redis, database, uptime, and WebSocket connection metrics.",
)
async def get_metrics():
    metrics = await health_service.get_metrics()
    return ApiResponse.ok(
        data=metrics.model_dump(mode="json"),
        message="System metrics",
    )
