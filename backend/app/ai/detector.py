"""
Detector — Phase 3 AI infrastructure.

Thin, stateless wrapper around ModelManager that runs YOLO inference
on a single frame and returns the raw Ultralytics Results object.

Design contract:
  - Accepts ONE numpy BGR frame (from OpenCV / FrameBuffer)
  - Returns the raw Results list — no filtering, no counting, no drawing
  - Logs inference time, device, image size, and detection count (Task 10)
  - Never raises — errors are caught, logged, and None is returned
  - detect() is SYNCHRONOUS — thread management is the caller's responsibility.
    At 130 req/s (13 cameras × 10 FPS) wrapping every call in asyncio.to_thread
    creates unnecessary scheduling overhead. The future AI Worker runs detect()
    directly inside its own thread; test endpoints call it synchronously.

Future AI modules (person counter, queue detector, zone monitor) must
call detector.detect() and then use the get_* helpers to extract data.
Never create another YOLO instance — always use ModelManager.
"""
import time
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

from app.ai.model_manager import model_manager


class Detector:
    """
    Stateless YOLO inference executor.

    Correct usage (sync context / AI Worker thread):
        results = detector.detect(frame)
        boxes = detector.get_boxes(results)
    """

    def detect(self, frame: np.ndarray) -> Optional[List[Any]]:
        """
        Run YOLO inference on a single BGR frame.

        Args:
            frame: numpy ndarray of shape (H, W, 3), BGR colour order.

        Returns:
            List[ultralytics.engine.results.Results] — raw model output.
            None — if the model is not loaded or an error occurs.
        """
        if not model_manager.is_loaded():
            logger.warning("Detector.detect() called but model is not loaded")
            return None

        if frame is None or frame.size == 0:
            logger.warning("Detector.detect() received an empty frame")
            return None

        model = model_manager.get_model()
        h, w = frame.shape[:2]

        try:
            t_start = time.monotonic()
            results = model(frame, verbose=False)
            elapsed_ms = (time.monotonic() - t_start) * 1000.0

            num_detections = len(results[0].boxes) if results else 0

            # Task 10 — performance log for every inference
            logger.info(
                "Inference | device={dev} | size={w}x{h} | "
                "detections={n} | time={t:.1f}ms",
                dev=model_manager.device,
                w=w,
                h=h,
                n=num_detections,
                t=elapsed_ms,
            )

            return results

        except Exception as exc:
            logger.error(
                "Inference failed | size={w}x{h} | error={err}",
                w=w,
                h=h,
                err=str(exc),
                exc_info=True,
            )
            return None

    # ─── Result Helpers ────────────────────────────────────────────────────────
    # Pure data extraction — no business logic, no filtering, no thresholds.
    # Future AI modules call these after detect() to unpack the raw Results.

    def get_boxes(self, results: Optional[List[Any]]) -> List[List[float]]:
        """
        Extract bounding box coordinates from raw Results.

        Returns:
            List of [x1, y1, x2, y2] in absolute pixel coordinates.
            Empty list if results is None or contains no detections.
        """
        if not results:
            return []
        try:
            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                return []
            return boxes.xyxy.cpu().tolist()   # [[x1,y1,x2,y2], ...]
        except Exception as exc:
            logger.error("get_boxes error | {err}", err=str(exc))
            return []

    def get_classes(self, results: Optional[List[Any]]) -> List[str]:
        """
        Extract detected class names from raw Results.

        Returns:
            List of class name strings in the same order as get_boxes().
            Empty list if results is None or contains no detections.
        """
        if not results:
            return []
        try:
            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                return []
            names = results[0].names                    # {int: str} class map
            cls_ids = boxes.cls.cpu().tolist()          # [0, 1, 0, ...]
            return [names[int(c)] for c in cls_ids]
        except Exception as exc:
            logger.error("get_classes error | {err}", err=str(exc))
            return []

    def get_confidence(self, results: Optional[List[Any]]) -> List[float]:
        """
        Extract confidence scores from raw Results.

        Returns:
            List of float confidence values in [0.0, 1.0].
            Empty list if results is None or contains no detections.
        """
        if not results:
            return []
        try:
            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                return []
            return [round(float(c), 4) for c in boxes.conf.cpu().tolist()]
        except Exception as exc:
            logger.error("get_confidence error | {err}", err=str(exc))
            return []

    def parse_results(
        self, results: Optional[List[Any]]
    ) -> Dict[str, List]:
        """
        Convenience wrapper — returns all three lists in one call.

        Returns:
            {
                "boxes":      [[x1,y1,x2,y2], ...],
                "classes":    ["person", ...],
                "confidence": [0.91, ...],
            }
        """
        return {
            "boxes":      self.get_boxes(results),
            "classes":    self.get_classes(results),
            "confidence": self.get_confidence(results),
        }


# ─── Singleton ─────────────────────────────────────────────────────────────────

detector: Detector = Detector()
