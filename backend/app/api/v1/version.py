"""Version API endpoint."""
from fastapi import APIRouter

from app.common.response import ApiResponse
from app.services.health.health_service import health_service

router = APIRouter()


@router.get(
    "",
    summary="Application version",
    description="Returns version, environment and API metadata. Useful in deployments to verify which build is running.",
)
async def get_version():
    version_info = health_service.get_version()
    return ApiResponse.ok(
        data=version_info.model_dump(mode="json"),
        message="Version information",
    )
