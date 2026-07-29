"""
AI API endpoints — Phase 3.

Routes:
    GET  /api/v1/ai/status       — model + GPU status
    POST /api/v1/ai/test         — upload one image, run inference, return counts only
    POST /api/v1/ai/test-camera  — run inference on a camera's latest live frame
"""
import time
import uuid
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from loguru import logger

from app.ai.detector import detector
from app.ai.gpu import get_gpu_info
from app.ai.model_manager import model_manager
from app.ai.schemas import InferenceStats, ModelStatus
from app.camera.camera_manager import camera_manager
from app.common.response import ApiResponse

router = APIRouter(tags=["AI"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /status  →  full path: /api/v1/ai/status
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/status",
    response_model=ApiResponse,
    summary="AI model and GPU status",
)
async def get_ai_status() -> ApiResponse:
    """
    Returns the current state of the YOLO model and GPU environment.

    - `model_loaded`  — True when YOLO is in memory and ready
    - `device`        — "cuda" or "cpu"
    - `model_name`    — e.g. "yolo11x.pt"
    - `gpu_available` — True when CUDA is detected
    - `gpu_name`      — GPU display name
    - `gpu_memory_mb` — Total VRAM in MB
    """
    gpu = get_gpu_info()

    data = ModelStatus(
        model_loaded=model_manager.is_loaded(),
        device=model_manager.device if model_manager.is_loaded() else gpu["device"],
        model_name=model_manager.model_name,
        model_path=model_manager.model_path,
        gpu_available=gpu["cuda_available"],
        gpu_name=gpu["gpu_name"],
        gpu_memory_mb=gpu["gpu_memory_mb"],
    )

    return ApiResponse.ok(data=data.model_dump(), message="AI status retrieved")


# ─────────────────────────────────────────────────────────────────────────────
# POST /test  →  full path: /api/v1/ai/test
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/test",
    response_model=ApiResponse,
    summary="Run YOLO inference on an uploaded image",
)
async def test_inference(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, BMP, etc.)"),
) -> ApiResponse:
    """
    Upload a single image and receive raw detection statistics.

    - Reads uploaded bytes into an OpenCV array (no disk write)
    - Calls detector.detect() synchronously — no asyncio.to_thread overhead
    - Returns only counts and timing — never returns image or bounding boxes

    Note on threading: detect() is synchronous. For a test/debug endpoint
    calling it directly in the async handler is acceptable (~50 ms GPU
    inference). Production AI Workers will call detect() inside their own
    dedicated threads.

    Response:
    ```json
    {
      "success": true,
      "detections": 5,
      "inference_time_ms": 42.3,
      "device": "cuda",
      "image_width": 1920,
      "image_height": 1080
    }
    ```
    """
    _require_model()

    frame, h, w = await _read_image_upload(file)

    # ── Run inference — direct sync call, no thread wrapper ───────────────────
    t_start = time.monotonic()
    try:
        results = detector.detect(frame)
    except Exception as exc:
        logger.error("test_inference error | {err}", err=str(exc))
        return ApiResponse.ok(
            data=InferenceStats(
                success=False,
                device=model_manager.device,
                image_width=w, image_height=h,
                error=str(exc),
            ).model_dump(),
            message="Inference failed",
        )
    elapsed_ms = (time.monotonic() - t_start) * 1000.0

    if results is None:
        return ApiResponse.ok(
            data=InferenceStats(
                success=False,
                device=model_manager.device,
                image_width=w, image_height=h,
                error="Detector returned no results",
            ).model_dump(),
            message="Inference returned no results",
        )

    num_detections = len(results[0].boxes) if results else 0
    return ApiResponse.ok(
        data=InferenceStats(
            success=True,
            detections=num_detections,
            inference_time_ms=round(elapsed_ms, 2),
            device=model_manager.device,
            image_width=w,
            image_height=h,
        ).model_dump(),
        message="Inference complete",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /test-camera  →  full path: /api/v1/ai/test-camera
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/test-camera",
    response_model=ApiResponse,
    summary="Run YOLO inference on a camera's latest live frame",
)
async def test_camera_inference(camera_id: uuid.UUID) -> ApiResponse:
    """
    Fetch the latest frame from a running camera stream and run YOLO inference.

    Flow:
        CameraManager → get_latest_frame(camera_id) → detector.detect() → stats

    Useful for debugging:
    - Verify a camera is streaming correctly
    - Confirm inference is working on real frames (not synthetic test images)
    - Check detection counts per camera without any AI worker running

    Returns only metadata — no image, no bounding boxes.
    """
    _require_model()

    # ── Fetch latest frame from FrameBuffer via CameraManager ─────────────────
    entry = await camera_manager.get_latest_frame(camera_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No frame available for camera {camera_id}. "
                "Ensure the camera is active and stream_enabled=True, "
                "then call POST /cameras/reload."
            ),
        )

    frame: Optional[np.ndarray] = entry.latest_frame
    if frame is None or frame.size == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Camera {camera_id} has an empty frame in buffer.",
        )

    h, w = frame.shape[:2]

    # ── Run inference — direct sync call ──────────────────────────────────────
    t_start = time.monotonic()
    try:
        results = detector.detect(frame)
    except Exception as exc:
        logger.error(
            "test_camera_inference error | camera_id={cid} | {err}",
            cid=camera_id,
            err=str(exc),
        )
        return ApiResponse.ok(
            data=InferenceStats(
                success=False,
                device=model_manager.device,
                image_width=w, image_height=h,
                error=str(exc),
            ).model_dump(),
            message="Inference failed",
        )
    elapsed_ms = (time.monotonic() - t_start) * 1000.0

    if results is None:
        return ApiResponse.ok(
            data=InferenceStats(
                success=False,
                device=model_manager.device,
                image_width=w, image_height=h,
                error="Detector returned no results",
            ).model_dump(),
            message="Inference returned no results",
        )

    num_detections = len(results[0].boxes) if results else 0

    return ApiResponse.ok(
        data={
            **InferenceStats(
                success=True,
                detections=num_detections,
                inference_time_ms=round(elapsed_ms, 2),
                device=model_manager.device,
                image_width=w,
                image_height=h,
            ).model_dump(),
            # Extra context useful for camera debugging
            "camera_id": str(camera_id),
            "frame_number": entry.frame_number,
            "frame_timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "stream_fps": entry.fps,
        },
        message=f"Camera inference complete | camera_id={camera_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _require_model() -> None:
    """Raise HTTP 503 if the YOLO model is not loaded."""
    if not model_manager.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YOLO model is not loaded. Check GET /api/v1/ai/status.",
        )


async def _read_image_upload(file: UploadFile):
    """
    Read an uploaded image file into a numpy BGR array.
    Returns (frame, height, width).
    Raises HTTP 400 / 422 on failure.
    """
    try:
        raw_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        )

    try:
        arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            raise ValueError(
                "cv2.imdecode returned None — unsupported format or corrupt file"
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid image: {exc}",
        )

    h, w = frame.shape[:2]
    return frame, h, w
