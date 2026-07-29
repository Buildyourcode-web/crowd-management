"""AI infrastructure package — YOLO model management and inference."""
from app.ai.model_manager import model_manager, ModelManager
from app.ai.detector import detector, Detector
from app.ai.gpu import get_gpu_info

__all__ = ["model_manager", "ModelManager", "detector", "Detector", "get_gpu_info"]
