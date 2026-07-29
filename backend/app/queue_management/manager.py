"""
QueueManager — global registry of QueueWorker instances (Task 5).

═══════════════════════════════════════════════════════════════════════
Queue Manager overview
═══════════════════════════════════════════════════════════════════════

QueueManager is a singleton that:
    • Maintains one QueueWorker per camera
    • Enforces the no-duplicate-worker constraint (returns False if
      a worker is already running for the requested camera)
    • Exposes start / stop / status for REST API handlers

Workers are started and stopped via REST API calls — QueueManager does
NOT auto-start workers at application startup. This gives operators
full control over which cameras are monitored.

═══════════════════════════════════════════════════════════════════════
REST API integration
═══════════════════════════════════════════════════════════════════════

    POST /queue/start/{camera_id}     → queue_manager.start_worker()
    POST /queue/stop/{camera_id}      → queue_manager.stop_worker()
    GET  /queue/status                → queue_manager.get_all_statuses()
    GET  /queue/status/{camera_id}    → queue_manager.get_status()
"""
import uuid
from typing import Dict, List, Optional

from loguru import logger

from app.queue_management.analyzer import DEFAULT_LOW_MAX, DEFAULT_MEDIUM_MAX
from app.queue_management.roi import QueueROI
from app.queue_management.schemas import QueueStatus
from app.queue_management.worker import QueueWorker, _DEFAULT_TARGET_FPS


class QueueManager:
    """
    Global registry for QueueWorker instances.

    One worker per camera. Thread-safe for asyncio (all operations are
    awaitable and run in the single-threaded event loop).
    """

    def __init__(self) -> None:
        self._workers: Dict[str, QueueWorker] = {}

    # ── Worker lifecycle ──────────────────────────────────────────────────────

    async def start_worker(
        self,
        camera_id: uuid.UUID,
        roi: QueueROI,
        target_fps: int = _DEFAULT_TARGET_FPS,
        low_max: int = DEFAULT_LOW_MAX,
        medium_max: int = DEFAULT_MEDIUM_MAX,
        direction: str = "UP",
        stabilization_sec: float = 3.0,
    ) -> bool:
        """
        Start a queue monitoring worker for camera_id.

        Args:
            camera_id:  UUID of the target camera.
            roi:        Rectangle ROI for queue counting.
            target_fps: Inference rate (default 5 FPS).
            low_max:    People count upper bound for LOW status.
            medium_max: People count upper bound for MEDIUM status.

        Returns:
            True  — worker started successfully.
            False — a worker is already running for this camera.
        """
        cam_id_str = str(camera_id)
        existing = self._workers.get(cam_id_str)
        if existing and existing.is_running:
            logger.warning(
                "QueueWorker already running | camera_id={cid}", cid=cam_id_str
            )
            return False

        worker = QueueWorker(
            camera_id, roi, target_fps, low_max, medium_max,
            direction=direction,
            stabilization_sec=stabilization_sec,
        )
        self._workers[cam_id_str] = worker
        await worker.start()
        return True

    async def stop_worker(self, camera_id: uuid.UUID) -> bool:
        """
        Stop the worker for camera_id.

        Returns:
            True  — worker stopped.
            False — no worker found for this camera.
        """
        cam_id_str = str(camera_id)
        worker = self._workers.get(cam_id_str)
        if not worker:
            return False
        await worker.stop()
        return True

    async def restart_worker(self, camera_id: uuid.UUID) -> bool:
        """
        Restart the worker for camera_id (Task 8).

        Returns:
            True  — worker restarted.
            False — no worker found for this camera.
        """
        cam_id_str = str(camera_id)
        worker = self._workers.get(cam_id_str)
        if not worker:
            return False
        await worker.restart()
        return True

    # ── Status queries ────────────────────────────────────────────────────────

    def get_status(self, camera_id: uuid.UUID) -> Optional[QueueStatus]:
        """Return status for one camera, or None if no worker exists."""
        worker = self._workers.get(str(camera_id))
        return worker.get_status() if worker else None

    def get_all_statuses(self) -> List[QueueStatus]:
        """Return status snapshots for all registered workers."""
        return [w.get_status() for w in self._workers.values()]

    @property
    def active_worker_count(self) -> int:
        """Number of currently running workers."""
        return sum(1 for w in self._workers.values() if w.is_running)


# ─── Singleton ────────────────────────────────────────────────────────────────

queue_manager: QueueManager = QueueManager()
