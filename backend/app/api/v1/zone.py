"""
Zone Monitoring REST API — Task 10.

═══════════════════════════════════════════════════════════════════════
REST API overview
═══════════════════════════════════════════════════════════════════════

    POST /zone/start/{camera_id}
        Body: {"zones": [{zone_id, zone_name, x1, y1, x2, y2}, ...]}
        Start zone monitoring with the given zone list.
        Validates: no duplicate zone IDs, no zero dimensions,
                   non-negative coordinates (Tasks 14, 15).
        Returns 409 if already running.
        Returns 503 if YOLO model not loaded.

    POST /zone/stop/{camera_id}
        Stop the zone monitoring worker.
        Returns 404 if no worker exists.

    GET /zone/status
        All cameras — list of ZoneCameraStatus.

    GET /zone/status/{camera_id}
        Single camera — ZoneCameraStatus.
        Returns 404 if no worker exists.
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from app.ai.model_manager import model_manager
from app.common.response import ApiResponse
from app.zone_monitoring.analyzer import (
    DEFAULT_HIGH_MAX,
    DEFAULT_LOW_MAX,
    DEFAULT_MEDIUM_MAX,
)
from app.zone_monitoring.manager import zone_manager
from app.zone_monitoring.schemas import ZoneStartRequest
from app.zone_monitoring.zone import Zone

router = APIRouter(tags=["Zone Monitoring"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /zone/start/{camera_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/zone/start/{camera_id}",
    response_model=ApiResponse,
    summary="Start zone monitoring for a camera",
)
async def start_zone(
    camera_id: uuid.UUID,
    body: ZoneStartRequest,
) -> ApiResponse:
    """
    Start zone monitoring for the specified camera.

    **Body** — one or more rectangle zone definitions:
    ```json
    {
        "zones": [
            {"zone_id": "A", "zone_name": "Entrance",
             "x1": 120, "y1": 150, "x2": 640, "y2": 540},
            {"zone_id": "B", "zone_name": "Exit",
             "x1": 650, "y1": 150, "x2": 1200, "y2": 540}
        ]
    }
    ```

    **Validation** (Task 15):
    - Duplicate zone IDs → **422**
    - Negative coordinates → **422**
    - Zero width or height → **422**

    **Returns** `409` if a worker is already running for this camera.
    **Returns** `503` if the YOLO model is not loaded.

    Overlapping zones are **allowed** but a warning is logged.
    Persons in the overlapping area are assigned to the first
    matching zone (first-match rule).
    """
    if not model_manager.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLO model not loaded. Check GET /api/v1/ai/status.",
        )

    # Build Zone objects from validated config
    zones = [
        Zone(
            zone_id=zc.zone_id,
            zone_name=zc.zone_name,
            x1=zc.x1,
            y1=zc.y1,
            x2=zc.x2,
            y2=zc.y2,
        )
        for zc in body.zones
    ]

    started = await zone_manager.start_worker(camera_id, zones)
    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A zone worker is already running for camera {camera_id}.",
        )

    logger.info(
        "ZoneWorker started via API | camera_id={cid} | zones={zids}",
        cid=camera_id,
        zids=[z.zone_id for z in zones],
    )
    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "started": True,
            "zones": [
                {
                    "zone_id":   z.zone_id,
                    "zone_name": z.zone_name,
                    "area_px2":  round(z.area()),
                    "center":    z.center(),
                }
                for z in zones
            ],
            "thresholds": {
                "LOW":      f"1–{DEFAULT_LOW_MAX}",
                "MEDIUM":   f"{DEFAULT_LOW_MAX + 1}–{DEFAULT_MEDIUM_MAX}",
                "HIGH":     f"{DEFAULT_MEDIUM_MAX + 1}–{DEFAULT_HIGH_MAX}",
                "CRITICAL": f"{DEFAULT_HIGH_MAX + 1}+",
            },
        },
        message=f"Zone monitoring started for camera {camera_id} "
                f"with {len(zones)} zone(s)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /zone/stop/{camera_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/zone/stop/{camera_id}",
    response_model=ApiResponse,
    summary="Stop zone monitoring for a camera",
)
async def stop_zone(camera_id: uuid.UUID) -> ApiResponse:
    """
    Stop the zone monitoring worker for the specified camera.

    Returns the final zone metrics in the response.
    **Returns** `404` if no worker is running for this camera.
    """
    final_status = zone_manager.get_status(camera_id)

    stopped = await zone_manager.stop_worker(camera_id)
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No zone worker found for camera {camera_id}.",
        )

    logger.info(
        "ZoneWorker stopped via API | camera_id={cid}", cid=camera_id
    )
    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "stopped": True,
            "final_metrics": final_status.model_dump() if final_status else {},
        },
        message=f"Zone monitoring stopped for camera {camera_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /zone/status   (all cameras)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/zone/status",
    response_model=ApiResponse,
    summary="Get zone status for all cameras",
)
async def get_all_zone_status() -> ApiResponse:
    """
    Returns current zone metrics for all cameras with registered workers.

    Includes both running and stopped workers.
    Use `worker_running` to distinguish.

    ```json
    {
      "cameras": [
        {
          "camera_id": "...",
          "worker_running": true,
          "zones": [
            {"zone_id": "A", "people_count": 18, "status": "MEDIUM", ...},
            {"zone_id": "B", "people_count": 37, "status": "HIGH",   ...}
          ],
          "fps": 4.9
        }
      ],
      "total_active_workers": 1
    }
    ```
    """
    statuses = zone_manager.get_all_statuses()
    return ApiResponse.ok(
        data={
            "cameras": [s.model_dump() for s in statuses],
            "total_active_workers": zone_manager.active_worker_count,
        },
        message="Zone status retrieved",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /zone/status/{camera_id}   (single camera)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/zone/status/{camera_id}",
    response_model=ApiResponse,
    summary="Get zone status for one camera",
)
async def get_camera_zone_status(camera_id: uuid.UUID) -> ApiResponse:
    """
    Returns live zone metrics for a specific camera.

    **Returns** `404` if no worker has been started for this camera.

    ```json
    {
      "camera_id": "...",
      "worker_running": true,
      "zones": [
        {
          "zone_id": "A", "zone_name": "Temple Entrance",
          "people_count": 18, "density": 0.089, "status": "MEDIUM"
        }
      ],
      "fps": 4.9,
      "last_updated": "2026-07-25T00:00:00+00:00"
    }
    ```
    """
    s = zone_manager.get_status(camera_id)
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No zone worker found for camera {camera_id}. "
                f"Use POST /api/v1/zone/start/{camera_id} first."
            ),
        )
    return ApiResponse.ok(data=s.model_dump(), message="Zone status retrieved")
