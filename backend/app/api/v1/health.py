"""Health check API endpoints."""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.services.health.health_service import health_service

router = APIRouter()


@router.get(
    "",
    summary="Overall health",
    description="Aggregate health status of all system components.",
)
async def overall_health():
    result = await health_service.get_overall_health()
    status_code = (
        status.HTTP_200_OK
        if result.status == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(
        status_code=status_code,
        content=ApiResponse.ok(data=result.model_dump(mode="json"), message="Health check").model_dump(mode="json"),
    )


@router.get(
    "/database",
    summary="Database health",
    description="PostgreSQL connectivity and latency check.",
)
async def database_health():
    result = await health_service.get_database_health()
    status_code = (
        status.HTTP_200_OK
        if result.status == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(
        status_code=status_code,
        content=ApiResponse.ok(data=result.model_dump(mode="json"), message="Database health").model_dump(mode="json"),
    )


@router.get(
    "/redis",
    summary="Redis health",
    description="Redis connectivity and latency check.",
)
async def redis_health():
    result = await health_service.get_redis_health()
    status_code = (
        status.HTTP_200_OK
        if result.status == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(
        status_code=status_code,
        content=ApiResponse.ok(data=result.model_dump(mode="json"), message="Redis health").model_dump(mode="json"),
    )


@router.get(
    "/application",
    summary="Application health",
    description="Application version, environment, and uptime.",
)
async def application_health():
    result = health_service.get_application_info()
    return ApiResponse.ok(
        data=result.model_dump(mode="json"),
        message="Application info",
    )
