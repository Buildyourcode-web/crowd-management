"""
FaceManager — global registry of FaceWorker instances (Task 8).
"""
import uuid
from typing import Dict, List, Optional

from loguru import logger

from app.face_recognition.matcher import DEFAULT_THRESHOLD
from app.face_recognition.schemas import FaceWorkerStatus
from app.face_recognition.worker import FaceWorker, _DEFAULT_TARGET_FPS, _COOLDOWN_SECONDS


class FaceManager:
    """
    Global registry for FaceWorker instances.
    One worker per camera — duplicate workers prevented.
    """

    def __init__(self) -> None:
        self._workers: Dict[str, FaceWorker] = {}

    async def start_worker(
        self,
        camera_id: uuid.UUID,
        threshold: float = DEFAULT_THRESHOLD,
        target_fps: int = _DEFAULT_TARGET_FPS,
        cooldown_seconds: int = _COOLDOWN_SECONDS,
    ) -> bool:
        """
        Start a face recognition worker for camera_id.

        Returns True on success, False if already running.
        """
        cam_id_str = str(camera_id)
        existing = self._workers.get(cam_id_str)
        if existing and existing.is_running:
            logger.warning(
                "FaceWorker already running | camera_id={cid}", cid=cam_id_str
            )
            return False

        worker = FaceWorker(camera_id, threshold, target_fps, cooldown_seconds)
        self._workers[cam_id_str] = worker
        await worker.start()
        return True

    async def stop_worker(self, camera_id: uuid.UUID) -> bool:
        """Stop the worker for camera_id. Returns False if not found."""
        cam_id_str = str(camera_id)
        worker = self._workers.get(cam_id_str)
        if not worker:
            return False
        await worker.stop()
        return True

    async def restart_worker(self, camera_id: uuid.UUID) -> bool:
        """Restart the worker for camera_id. Returns False if not found."""
        cam_id_str = str(camera_id)
        worker = self._workers.get(cam_id_str)
        if not worker:
            return False
        await worker.restart()
        return True

    def get_status(self, camera_id: uuid.UUID) -> Optional[FaceWorkerStatus]:
        """Return status for one camera, or None if no worker exists."""
        worker = self._workers.get(str(camera_id))
        return worker.get_status() if worker else None

    def get_all_statuses(self) -> List[FaceWorkerStatus]:
        """Return status for all registered workers."""
        return [w.get_status() for w in self._workers.values()]

    @property
    def active_worker_count(self) -> int:
        return sum(1 for w in self._workers.values() if w.is_running)


# ─── Singleton ────────────────────────────────────────────────────────────────

face_manager: FaceManager = FaceManager()
