"""
ModelManager — Tasks 3, 4, 12, 13.

Loads ONE YOLO model instance and keeps it in memory for the lifetime
of the application. Every future AI module (person counter, queue manager,
zone manager, face recognition) must call ModelManager.get_model() instead
of instantiating YOLO directly.

Architecture contract:
    ┌─────────────────────────────────────────────┐
    │  CameraManager → frame → Detector.detect()  │
    │                               │             │
    │              ModelManager.get_model()        │
    │                               │             │
    │              (single YOLO instance)          │
    └─────────────────────────────────────────────┘

Future modules that need YOLO:
    from app.ai.model_manager import model_manager
    model = model_manager.get_model()   # never call YOLO() directly
"""
import os
from typing import Any, Optional

from loguru import logger

from app.ai.gpu import get_gpu_info
from app.config.settings import settings


class ModelManager:
    """
    Singleton YOLO model owner.

    Public API:
        load_model()    → bool       Load the model from disk (blocking).
        get_model()     → YOLO|None  Return the live model instance.
        is_loaded()     → bool       True when model is ready for inference.
        unload_model()  → None       Release model memory (shutdown / testing).

    Thread-safety:
        load_model() is intended to be called ONCE during FastAPI startup
        (inside asyncio.to_thread / run_in_executor). All subsequent callers
        use get_model() which is a simple attribute read — inherently safe.
    """

    def __init__(self) -> None:
        self._model: Optional[Any] = None       # ultralytics.YOLO instance
        self._device: str = "cpu"
        self._model_path: str = settings.AI_MODEL_PATH
        self._model_name: str = settings.AI_MODEL_NAME

    # ─── Public Interface ─────────────────────────────────────────────────────

    def load_model(self) -> bool:
        """
        Load the YOLO model from settings.AI_MODEL_PATH.

        - Detects GPU automatically (or uses settings.AI_DEVICE if set).
        - Runs a silent warm-up inference to pre-allocate CUDA memory.
        - Returns True on success, False on any failure.
        - Never raises — errors are logged and False is returned.
        """
        if self._model is not None:
            logger.info("Model already loaded — skipping duplicate load")
            return True

        try:
            from ultralytics import YOLO  # lazy import — avoids import-time crash

            # Resolve device
            gpu_info = get_gpu_info()
            if settings.AI_DEVICE == "auto":
                self._device = gpu_info["device"]
            else:
                self._device = settings.AI_DEVICE

            # Validate model path
            abs_path = os.path.abspath(self._model_path)
            if not os.path.isfile(abs_path):
                logger.error(
                    "Model file not found | path={p}", p=abs_path
                )
                return False

            logger.info(
                "Loading YOLO model | path={p} | device={d}",
                p=abs_path,
                d=self._device,
            )

            # Load model (with fallback if local file is a Git LFS pointer text file)
            try:
                self._model = YOLO(abs_path)
            except Exception as load_err:
                logger.warning(
                    "Local model loading failed ({err}) — downloading standard yolo11n.pt model...",
                    err=str(load_err),
                )
                self._model = YOLO("yolo11n.pt")

            self._model.to(self._device)

            # Warm-up: silent inference on a standard 640×640 blank image.
            # 640×640 is the default YOLO input stride — this ensures CUDA
            # allocates the correct memory blocks for real inference sizes.
            import numpy as np
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model(dummy, verbose=False)

            logger.info(
                "YOLO model loaded and warmed up | name={n} | device={d}",
                n=self._model_name,
                d=self._device,
            )
            return True

        except ImportError:
            logger.error("ultralytics is not installed — cannot load YOLO model")
            return False
        except Exception as exc:
            logger.error(
                "Model loading failed | error={err}", err=str(exc), exc_info=True
            )
            self._model = None
            return False

    def get_model(self) -> Optional[Any]:
        """
        Return the loaded YOLO model instance, or None if not yet loaded.

        Future AI modules MUST use this method.
        They must NEVER call YOLO(...) directly.
        """
        return self._model

    def is_loaded(self) -> bool:
        """True when the model is in memory and ready for inference."""
        return self._model is not None

    def unload_model(self) -> None:
        """
        Release the model from memory.
        Called during application shutdown or in tests.
        """
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("YOLO model unloaded | name={n}", n=self._model_name)

    # ─── Status Helpers ───────────────────────────────────────────────────────

    @property
    def device(self) -> str:
        """The device the model is currently running on."""
        return self._device

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_path(self) -> str:
        return self._model_path


# ─── Singleton ────────────────────────────────────────────────────────────────
# Import this object everywhere — never instantiate ModelManager directly.

model_manager: ModelManager = ModelManager()
