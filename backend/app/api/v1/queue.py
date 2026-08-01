"""
Queue Management REST API — Task 7.

═══════════════════════════════════════════════════════════════════════
REST API overview
═══════════════════════════════════════════════════════════════════════

    POST /queue/start/{camera_id}
        Body: {"x1":100, "y1":200, "x2":900, "y2":650}
        Start a queue monitoring worker with the given ROI.
        Returns 409 if already running.
        Returns 503 if YOLO model not loaded.

    POST /queue/stop/{camera_id}
        Stop the worker for a camera.
        Returns 404 if no worker exists.

    GET /queue/status
        All cameras — returns list of QueueStatus.

    GET /queue/status/{camera_id}
        Single camera — returns QueueStatus.
        Returns 404 if no worker exists.
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from app.ai.model_manager import model_manager
from app.common.response import ApiResponse
from app.queue_management.analyzer import DEFAULT_LOW_MAX, DEFAULT_MEDIUM_MAX
from app.queue_management.manager import queue_manager
from app.queue_management.roi import QueueROI
from app.queue_management.schemas import QueueROIConfig

router = APIRouter(tags=["Queue Management"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /queue/start/{camera_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/queue/start/{camera_id}",
    response_model=ApiResponse,
    summary="Start queue monitoring worker for a camera",
)
async def start_queue(
    camera_id: uuid.UUID,
    roi_config: QueueROIConfig,
) -> ApiResponse:
    """
    Start a queue monitoring worker for the specified camera.

    **Body** — queue ROI in absolute pixel coordinates + queue direction:
    ```json
    {
      "x1": 100, "y1": 200, "x2": 900, "y2": 650,
      "direction": "UP"
    }
    ```

    **direction** tells the system which way people walk through the queue:
    - `UP`    — people move toward smaller Y (gate at top of frame)
    - `DOWN`  — people move toward larger  Y (gate at bottom)
    - `LEFT`  — people move toward smaller X (gate at left)
    - `RIGHT` — people move toward larger  X (gate at right)
    - `ANY`   — Euclidean distance (no directional filter, legacy mode)

    Only **forward movement** along this direction contributes to queue speed.
    Head turns, side steps, shoulder sways are ignored.

    The ROI rectangle defines the queue area. Only persons whose
    bounding box centroid is inside this rectangle are counted.

    **Returns** `409` if a worker is already running for this camera.
    **Returns** `503` if the YOLO model is not loaded.
    """
    if not model_manager.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLO model not loaded. Check GET /api/v1/ai/status.",
        )

    roi = QueueROI(
        x1=roi_config.x1,
        y1=roi_config.y1,
        x2=roi_config.x2,
        y2=roi_config.y2,
    )

    started = await queue_manager.start_worker(
        camera_id, roi,
        direction=roi_config.direction,
        stabilization_sec=roi_config.stabilization_sec,
    )
    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A queue worker is already running for camera {camera_id}.",
        )

    logger.info(
        "QueueWorker started via API | camera_id={cid} | roi={roi}",
        cid=camera_id,
        roi=repr(roi),
    )
    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "started": True,
            "roi": roi_config.model_dump(),
            "thresholds": {
                "LOW": f"1–{DEFAULT_LOW_MAX}",
                "MEDIUM": f"{DEFAULT_LOW_MAX + 1}–{DEFAULT_MEDIUM_MAX}",
                "HIGH": f"{DEFAULT_MEDIUM_MAX + 1}+",
            },
        },
        message=f"Queue monitoring started for camera {camera_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /queue/stop/{camera_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/queue/stop/{camera_id}",
    response_model=ApiResponse,
    summary="Stop queue monitoring worker for a camera",
)
async def stop_queue(camera_id: uuid.UUID) -> ApiResponse:
    """
    Stop the queue monitoring worker for the specified camera.

    Returns the final queue metrics in the response.
    **Returns** `404` if no worker is running for this camera.
    """
    final_status = queue_manager.get_status(camera_id)

    stopped = await queue_manager.stop_worker(camera_id)
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No queue worker found for camera {camera_id}.",
        )

    logger.info(
        "QueueWorker stopped via API | camera_id={cid}", cid=camera_id
    )
    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "stopped": True,
            "final_metrics": final_status.model_dump() if final_status else {},
        },
        message=f"Queue monitoring stopped for camera {camera_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /queue/status   (all cameras)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/queue/status",
    response_model=ApiResponse,
    summary="Get queue status for all cameras",
)
async def get_all_queue_status() -> ApiResponse:
    """
    Returns current queue metrics for all cameras with registered workers.

    Includes both running and stopped workers.
    Use `worker_running` field to distinguish.

    ```json
    {
      "cameras": [
        {
          "camera_id": "...",
          "worker_running": true,
          "people_inside_queue": 18,
          "queue_length": 18,
          "queue_status": "MEDIUM",
          "fps": 4.9
        }
      ],
      "total_active_workers": 1
    }
    ```
    """
    statuses = queue_manager.get_all_statuses()
    return ApiResponse.ok(
        data={
            "cameras": [s.model_dump() for s in statuses],
            "total_active_workers": queue_manager.active_worker_count,
        },
        message="Queue status retrieved",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /queue/status/{camera_id}   (single camera)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/queue/status/{camera_id}",
    response_model=ApiResponse,
    summary="Get queue status for one camera",
)
async def get_camera_queue_status(camera_id: uuid.UUID) -> ApiResponse:
    """
    Returns live queue metrics for a specific camera.

    Returns an idle status (worker_running=false) if no worker has been started,
    instead of raising a 404, to avoid error spam from frontend polling.

    ```json
    {
      "camera_id": "...",
      "worker_running": false,
      "people_inside_queue": 0,
      "queue_length": 0,
      "queue_status": "LOW",
      "fps": 0
    }
    ```
    """
    s = queue_manager.get_status(camera_id)
    if s is None:
        # Return idle payload instead of 404 — the frontend polls this endpoint
        # continuously; a 404 floods the logs and triggers error UI states.
        return ApiResponse.ok(
            data={
                "camera_id": str(camera_id),
                "worker_running": False,
                "people_inside_queue": 0,
                "queue_length": 0,
                "queue_status": "LOW",
                "avg_wait_seconds": None,
                "fps": 0,
                "last_updated": None,
            },
            message="No queue worker running for this camera",
        )
    return ApiResponse.ok(data=s.model_dump(), message="Queue status retrieved")
