"""
AI response schemas — Task 6.

Pydantic models for AI status and inference responses.
Used exclusively by the AI API endpoints.
"""
from typing import Optional

from pydantic import BaseModel


class GPUInfo(BaseModel):
    """GPU / CUDA environment information."""

    device: str                         # "cuda" or "cpu"
    gpu_name: Optional[str] = None      # e.g. "NVIDIA GeForce RTX 3050 6GB Laptop GPU"
    gpu_memory_mb: Optional[int] = None # Total VRAM in megabytes
    cuda_available: bool = False
    torch_version: str = "unknown"
    cuda_version: Optional[str] = None


class ModelStatus(BaseModel):
    """
    Current state of the YOLO model.
    Returned by GET /api/v1/ai/status.
    """

    model_loaded: bool
    device: str
    model_name: str
    model_path: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    gpu_memory_mb: Optional[int] = None


class InferenceStats(BaseModel):
    """
    Result of a single inference run.
    Returned by POST /api/v1/ai/test.

    Note: never contains image data, bounding boxes, or pixel arrays.
    """

    success: bool
    detections: int = 0             # Number of bounding boxes returned
    inference_time_ms: float = 0.0  # Wall-clock time for model.predict()
    device: str = "cpu"
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    error: Optional[str] = None     # Populated only when success=False
