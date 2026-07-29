"""
Person Counter REST API — Tasks 8, 9.

Routes:
    POST /person-counter/start/{camera_id}   — start worker
    POST /person-counter/stop/{camera_id}    — stop worker
    GET  /person-counter/status              — all cameras
    GET  /person-counter/status/{camera_id} — single camera
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from app.ai.model_manager import model_manager
from app.common.response import ApiResponse
from app.person_counter.roi import CountingLine
from app.person_counter.schemas import CountingLineConfig
from app.person_counter.worker import person_counter_manager

router = APIRouter(tags=["Person Counter"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /person-counter/start/{camera_id}   (Task 9)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/person-counter/start/{camera_id}",
    response_model=ApiResponse,
    summary="Start person counting worker for a camera",
)
async def start_counter(
    camera_id: uuid.UUID,
    line_config: CountingLineConfig,
) -> ApiResponse:
    """
    Start a person counting worker for the specified camera.

    **Requires**: Camera must be active and stream-enabled
    (check POST /cameras/reload if cameras were recently configured).

    **Body** — counting line in absolute pixel coordinates:
    ```json
    {"start_x": 0, "start_y": 360, "end_x": 1280, "end_y": 360}
    ```

    **Line orientation**:
    - Horizontal (`|dx| >= |dy|`): Top→Bottom = Entry
    - Vertical (`|dy| > |dx|`): Left→Right = Entry

    **Returns** `409` if a worker is already running for this camera.
    **Returns** `503` if the YOLO model is not loaded.
    """
    if not model_manager.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLO model not loaded. Check GET /api/v1/ai/status.",
        )

    counting_line = CountingLine(
        start_x=line_config.start_x,
        start_y=line_config.start_y,
        end_x=line_config.end_x,
        end_y=line_config.end_y,
    )

    started = await person_counter_manager.start_worker(camera_id, counting_line)
    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A worker is already running for camera {camera_id}.",
        )

    orientation = "horizontal" if counting_line.is_horizontal else "vertical"
    logger.info(
        "PersonCounter started via API | camera_id={cid} | "
        "line=({sx:.0f},{sy:.0f})→({ex:.0f},{ey:.0f}) | {orient}",
        cid=camera_id,
        sx=line_config.start_x,
        sy=line_config.start_y,
        ex=line_config.end_x,
        ey=line_config.end_y,
        orient=orientation,
    )
    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "started": True,
            "line": line_config.model_dump(),
            "orientation": orientation,
        },
        message=f"Person counter started for camera {camera_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /person-counter/stop/{camera_id}   (Task 9)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/person-counter/stop/{camera_id}",
    response_model=ApiResponse,
    summary="Stop person counting worker for a camera",
)
async def stop_counter(camera_id: uuid.UUID) -> ApiResponse:
    """
    Stop the person counting worker for the specified camera.

    Returns **404** if no worker is running for this camera.
    The final counts are returned in the response.
    """
    # Grab final status before stopping
    status_before = person_counter_manager.get_status(camera_id)

    stopped = await person_counter_manager.stop_worker(camera_id)
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No worker found for camera {camera_id}.",
        )

    logger.info(
        "PersonCounter stopped via API | camera_id={cid}", cid=camera_id
    )
    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "stopped": True,
            "final_counts": status_before.model_dump() if status_before else {},
        },
        message=f"Person counter stopped for camera {camera_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /person-counter/status   (Task 8 — all cameras)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/person-counter/status",
    response_model=ApiResponse,
    summary="Get person count status for all cameras",
)
async def get_all_status() -> ApiResponse:
    """
    Returns current entry / exit / occupancy for every registered worker.

    Response includes both running and stopped workers.
    Use `worker_running` to distinguish.

    ```json
    {
      "cameras": [
        {
          "camera_id": "...",
          "entry_count": 25,
          "exit_count": 18,
          "current_occupancy": 7,
          "worker_running": true,
          "fps": 9.8
        }
      ],
      "total_active_workers": 1
    }
    ```
    """
    statuses = person_counter_manager.get_all_statuses()
    return ApiResponse.ok(
        data={
            "cameras": [s.model_dump() for s in statuses],
            "total_active_workers": person_counter_manager.active_worker_count,
        },
        message="Person counter status retrieved",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /person-counter/status/{camera_id}   (Task 8 — single camera)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/person-counter/status/{camera_id}",
    response_model=ApiResponse,
    summary="Get person count status for one camera",
)
async def get_camera_status(camera_id: uuid.UUID) -> ApiResponse:
    """
    Returns live entry / exit / occupancy for a specific camera.

    **Returns** `404` if no worker has been started for this camera.

    ```json
    {
      "camera_id": "...",
      "entry_count": 25,
      "exit_count": 18,
      "current_occupancy": 7,
      "worker_running": true,
      "fps": 9.8,
      "last_updated": "2026-07-25T00:00:00+00:00"
    }
    ```
    """
    s = person_counter_manager.get_status(camera_id)
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No worker found for camera {camera_id}. "
                   f"Use POST /api/v1/person-counter/start/{camera_id} first.",
        )
    return ApiResponse.ok(data=s.model_dump(), message="Status retrieved")
