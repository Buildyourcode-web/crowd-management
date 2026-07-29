"""
Face Detector — InsightFace model manager + detector wrapper (Task 3, 13).

═══════════════════════════════════════════════════════════════════════
Architecture
═══════════════════════════════════════════════════════════════════════

FaceModelManager (singleton)
    └── loads InsightFace buffalo_l ONCE
    └── GPU: CUDAExecutionProvider (RTX 3050)
    └── CPU fallback: CPUExecutionProvider

FaceDetector (singleton, thin wrapper)
    └── calls face_model_manager.get_app().get(frame)
    └── returns List[FaceResult]
    └── SYNCHRONOUS — call via asyncio.to_thread from workers

═══════════════════════════════════════════════════════════════════════
InsightFace buffalo_l model pack
═══════════════════════════════════════════════════════════════════════

Downloaded automatically to ~/.insightface/models/buffalo_l/ on first
use (~300 MB). Contains:

    det_10g.onnx       — SCRFD face detector
    w600k_r50.onnx     — ArcFace ResNet-50 recognition model

Each face returned by app.get(frame) has:
    face.bbox          — [x1, y1, x2, y2] in pixels
    face.det_score     — detection confidence [0.0, 1.0]
    face.kps           — 5×2 landmark keypoints
    face.embedding     — 512-dim ArcFace float32 embedding

InsightFace internally normalizes embeddings. We re-normalize for safety.

═══════════════════════════════════════════════════════════════════════
ensure_loaded() design
═══════════════════════════════════════════════════════════════════════

ensure_loaded() is IDEMPOTENT and THREAD-SAFE (protected by threading.Lock).
It is called:
    1. By FaceWorker.start() via asyncio.to_thread — loads model once
       when the first camera worker starts.
    2. By POST /face/register — ensures model is ready before registration.

After the first load, all subsequent calls are instant no-ops.
The model is NEVER reloaded during the lifetime of the process.
"""
import threading
from dataclasses import dataclass, field
from typing import Any, List, Optional

import numpy as np
from loguru import logger

from app.face_recognition.embedding import normalize_embedding

# Minimum face quality thresholds (Task 15)
MIN_DETECTION_SCORE: float = 0.5   # reject low-confidence faces during registration
MIN_FACE_SIZE_PX: int = 40         # reject very small faces (width or height < 40px)


@dataclass
class FaceResult:
    """
    Result for one detected face.

    bbox:       [x1, y1, x2, y2] in pixel coordinates
    confidence: SCRFD detection score [0.0, 1.0]
    landmarks:  5 keypoints [[x,y], ...], or None
    embedding:  512-dim L2-normalized ArcFace float32 array
    """
    bbox: List[float]
    confidence: float
    landmarks: Optional[List[List[float]]]
    embedding: np.ndarray = field(repr=False)

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    def is_too_small(self, min_px: int = MIN_FACE_SIZE_PX) -> bool:
        return self.width < min_px or self.height < min_px

    def is_low_quality(self, min_score: float = MIN_DETECTION_SCORE) -> bool:
        return self.confidence < min_score


class FaceModelManager:
    """
    InsightFace model singleton.

    Loads the buffalo_l model pack ONCE (GPU first, CPU fallback).
    Thread-safe — protected by threading.Lock.

    Usage:
        face_model_manager.ensure_loaded()   # call before first use
        app = face_model_manager.get_app()
        faces = app.get(frame)
    """

    def __init__(self) -> None:
        self._app: Optional[Any] = None
        self._loaded: bool = False
        self._lock = threading.Lock()

    def ensure_loaded(self, ctx_id: int = 0) -> None:
        """
        Load InsightFace buffalo_l if not already loaded. Idempotent.

        Args:
            ctx_id: ONNX device context.
                    0  → GPU (CUDA, default for RTX 3050)
                    -1 → CPU

        Downloads ~300 MB of ONNX models on first call.
        Subsequent calls are instant no-ops (lock-protected).
        """
        with self._lock:
            if self._loaded:
                return
            logger.info(
                "FaceModelManager | Loading InsightFace buffalo_l | "
                "ctx_id={ctx} | providers=[CUDAExecutionProvider, CPUExecutionProvider]",
                ctx=ctx_id,
            )
            try:
                from insightface.app import FaceAnalysis
                self._app = FaceAnalysis(
                    name="buffalo_l",
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                )
                self._app.prepare(ctx_id=ctx_id, det_size=(640, 640))
                self._loaded = True
                logger.info(
                    "FaceModelManager | InsightFace buffalo_l loaded | "
                    "models: detection + ArcFace 512-dim"
                )
            except Exception as exc:
                logger.error(
                    "FaceModelManager | Failed to load InsightFace | {err}",
                    err=str(exc),
                    exc_info=True,
                )
                raise

    def get_app(self) -> Optional[Any]:
        """Return the loaded FaceAnalysis app, or None if not loaded."""
        return self._app

    def is_loaded(self) -> bool:
        return self._loaded


class FaceDetector:
    """
    Thin, stateless wrapper around FaceModelManager.

    Usage (synchronous — always call via asyncio.to_thread):
        results = face_detector.detect(frame)
        # results: List[FaceResult]

    Never creates a new InsightFace instance — always uses the singleton.
    """

    def detect(self, frame: np.ndarray) -> List[FaceResult]:
        """
        Detect all faces in a BGR frame and extract embeddings.

        Pipeline:
            frame → InsightFace SCRFD detector → face bboxes + landmarks
                  → ArcFace model             → 512-dim embeddings
            Then: L2-normalize each embedding

        Args:
            frame: BGR numpy array (from OpenCV / FrameBuffer).

        Returns:
            List[FaceResult] — one entry per detected face.
            Empty list if model not loaded, frame is empty, or no faces.
            Never raises — errors are caught and logged.
        """
        app = face_model_manager.get_app()
        if app is None:
            logger.warning("FaceDetector.detect() called but model is not loaded")
            return []

        if frame is None or frame.size == 0:
            logger.warning("FaceDetector.detect() received an empty frame")
            return []

        try:
            faces = app.get(frame)
        except Exception as exc:
            logger.error(
                "FaceDetector inference failed | {err}", err=str(exc), exc_info=True
            )
            return []

        if not faces:
            return []

        results: List[FaceResult] = []
        for f in faces:
            try:
                emb = getattr(f, "embedding", None)
                if emb is None:
                    continue  # No recognition model output — skip

                results.append(
                    FaceResult(
                        bbox=f.bbox.tolist(),
                        confidence=float(f.det_score),
                        landmarks=f.kps.tolist() if f.kps is not None else None,
                        embedding=normalize_embedding(emb),
                    )
                )
            except Exception as exc:
                logger.warning("FaceDetector parse face error | {err}", err=str(exc))

        return results


# ─── Singletons ───────────────────────────────────────────────────────────────

face_model_manager: FaceModelManager = FaceModelManager()
face_detector: FaceDetector = FaceDetector()
