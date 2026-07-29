"""
Camera stream management API endpoints.

New routes (Phase 2):
    GET  /api/v1/cameras/live            — live status of all stream workers
    GET  /api/v1/cameras/{id}/health     — latest health record + live FPS
    POST /api/v1/cameras/{id}/restart    — restart RTSP worker for one camera
    POST /api/v1/cameras/reload          — reload all cameras from DB

IMPORTANT: This router MUST be registered BEFORE the Phase 1 cameras router
in router.py so that the static path  /cameras/live  takes precedence over
the dynamic path  /cameras/{camera_id}.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.camera.camera_manager import camera_manager
from app.common.response import ApiResponse
from app.database.connection import get_db
from app.models.camera import Camera
from app.models.camera_health import CameraHealth

router = APIRouter(tags=["Camera Stream"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /cameras/live
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cameras/live",
    response_model=ApiResponse,
    summary="List all cameras with live stream status",
)
async def list_live_cameras(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Returns every stream-enabled camera merged with its live worker state.

    Fields:
    - `is_streaming`  — worker is running
    - `is_connected`  — RTSP connection is healthy right now
    - `fps`           — current measured frames-per-second
    - `total_frames`  — cumulative frames captured this session
    """
    # DB cameras that have streaming enabled
    result = await db.execute(
        select(Camera).where(
            Camera.is_active.is_(True),
            Camera.stream_enabled.is_(True),
        )
    )
    cameras: List[Camera] = list(result.scalars().all())

    # Index worker statuses by camera_id string
    worker_map: Dict[str, Dict[str, Any]] = {
        s["camera_id"]: s for s in camera_manager.get_all_statuses()
    }

    payload: List[Dict[str, Any]] = []
    for cam in cameras:
        cam_id = str(cam.id)
        ws = worker_map.get(cam_id, {})
        payload.append(
            {
                "camera_id": cam_id,
                "camera_name": cam.camera_name,
                "location": cam.location,
                "camera_type": cam.camera_type,
                "status": cam.status,
                "stream_enabled": cam.stream_enabled,
                "ai_enabled": cam.ai_enabled,
                "is_streaming": ws.get("is_running", False),
                "is_connected": ws.get("is_connected", False),
                "fps": ws.get("fps", 0.0),
                "total_frames": ws.get("total_frames", 0),
                "last_frame_time": (
                    cam.last_frame_time.isoformat()
                    if cam.last_frame_time
                    else None
                ),
                "last_health_check": (
                    cam.last_health_check.isoformat()
                    if cam.last_health_check
                    else None
                ),
            }
        )

    return ApiResponse.ok(
        data=payload,
        message=f"{len(payload)} stream-enabled camera(s)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /cameras/{camera_id}/health
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cameras/{camera_id}/health",
    response_model=ApiResponse,
    summary="Get latest health record and live status for a camera",
)
async def get_camera_health(
    camera_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Returns:
    - Live worker state (is_connected, live_fps) from the in-process CameraManager
    - The most recent CameraHealth row persisted to PostgreSQL
    """
    # Verify camera exists
    cam_result = await db.execute(
        select(Camera).where(Camera.id == camera_id)
    )
    camera: Optional[Camera] = cam_result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Latest DB health record
    health_result = await db.execute(
        select(CameraHealth)
        .where(CameraHealth.camera_id == camera_id)
        .order_by(CameraHealth.recorded_at.desc())
        .limit(1)
    )
    health: Optional[CameraHealth] = health_result.scalar_one_or_none()

    # Live worker snapshot
    worker = camera_manager.get_worker(camera_id)

    data: Dict[str, Any] = {
        "camera_id": str(camera_id),
        "camera_name": camera.camera_name,
        "db_status": camera.status,
        "stream_enabled": camera.stream_enabled,
        # ── Live (in-process) ───────────────────────────────────────────────
        "live": {
            "is_streaming": worker.is_running if worker else False,
            "is_connected": worker.is_connected if worker else False,
            "fps": worker.current_fps if worker else 0.0,
            "total_frames": worker.total_frames if worker else 0,
        },
        # ── Last DB health snapshot ──────────────────────────────────────────
        "last_health_record": (
            {
                "fps": health.fps,
                "error_message": health.error_message,
                "recorded_at": health.recorded_at.isoformat(),
            }
            if health
            else None
        ),
        "last_frame_time": (
            camera.last_frame_time.isoformat()
            if camera.last_frame_time
            else None
        ),
        "last_health_check": (
            camera.last_health_check.isoformat()
            if camera.last_health_check
            else None
        ),
    }

    return ApiResponse.ok(data=data, message="Camera health")


# ─────────────────────────────────────────────────────────────────────────────
# POST /cameras/{camera_id}/restart
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/cameras/{camera_id}/restart",
    response_model=ApiResponse,
    summary="Restart the RTSP stream worker for a camera",
)
async def restart_camera_stream(camera_id: uuid.UUID) -> ApiResponse:
    """
    Stops the current StreamWorker and spawns a fresh one.
    Re-reads the RTSP URL from the database so URL changes take effect.
    """
    logger.info("API: restart camera stream | camera_id={cid}", cid=camera_id)
    success = await camera_manager.restart_camera(camera_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Cannot restart camera {camera_id}. "
                "Camera not found, is inactive, or stream_enabled=False."
            ),
        )

    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "restarted_at": datetime.now(timezone.utc).isoformat(),
        },
        message=f"Camera {camera_id} stream restarted successfully",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /cameras/reload
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/cameras/reload",
    response_model=ApiResponse,
    summary="Reload all cameras from the database",
)
async def reload_all_cameras() -> ApiResponse:
    """
    Synchronises running workers with the database:
    - Starts workers for newly stream-enabled cameras
    - Stops workers for cameras that are deactivated or stream-disabled

    Returns a summary with counts of started, stopped, and total active workers.
    """
    logger.info("API: reload all cameras")
    summary = await camera_manager.reload_cameras()

    return ApiResponse.ok(
        data=summary,
        message="Camera reload complete",
    )
