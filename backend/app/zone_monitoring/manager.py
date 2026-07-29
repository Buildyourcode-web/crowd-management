"""
ZoneManager — global registry of ZoneWorker instances (Task 8).

═══════════════════════════════════════════════════════════════════════
Zone Manager overview
═══════════════════════════════════════════════════════════════════════

ZoneManager is a singleton that:
    • Maintains one ZoneWorker per camera
    • Enforces no-duplicate-worker constraint
    • Exposes start / stop / restart / status for REST API handlers

Workers are started via REST API — no auto-start at application startup.

═══════════════════════════════════════════════════════════════════════
REST API integration
═══════════════════════════════════════════════════════════════════════

    POST /zone/start/{camera_id}  → zone_manager.start_worker()
    POST /zone/stop/{camera_id}   → zone_manager.stop_worker()
    GET  /zone/status             → zone_manager.get_all_statuses()
    GET  /zone/status/{camera_id} → zone_manager.get_status()
"""
import uuid
from typing import Dict, List, Optional

from loguru import logger

from app.zone_monitoring.analyzer import (
    DEFAULT_HIGH_MAX,
    DEFAULT_LOW_MAX,
    DEFAULT_MEDIUM_MAX,
)
from app.zone_monitoring.schemas import ZoneCameraStatus
from app.zone_monitoring.worker import ZoneWorker, _DEFAULT_TARGET_FPS
from app.zone_monitoring.zone import Zone


class ZoneManager:
    """
    Global registry for ZoneWorker instances.

    One worker per camera. All operations are async-safe (cooperative
    multitasking via the single-threaded event loop — no locks needed).
    """

    def __init__(self) -> None:
        self._workers: Dict[str, ZoneWorker] = {}

    # ── Worker lifecycle ──────────────────────────────────────────────────────

    async def start_worker(
        self,
        camera_id: uuid.UUID,
        zones: List[Zone],
        target_fps: int = _DEFAULT_TARGET_FPS,
        low_max: int = DEFAULT_LOW_MAX,
        medium_max: int = DEFAULT_MEDIUM_MAX,
        high_max: int = DEFAULT_HIGH_MAX,
    ) -> bool:
        """
        Start a zone monitoring worker for camera_id.

        Args:
            camera_id:  UUID of the target camera.
            zones:      List of configured Zone objects.
            target_fps: Inference rate (default 5 FPS).
            low_max:    People count upper bound for LOW status.
            medium_max: People count upper bound for MEDIUM status.
            high_max:   People count upper bound for HIGH status.

        Returns:
            True  — worker started successfully.
            False — a worker is already running for this camera.
        """
        cam_id_str = str(camera_id)
        existing = self._workers.get(cam_id_str)
        if existing and existing.is_running:
            logger.warning(
                "ZoneWorker already running | camera_id={cid}", cid=cam_id_str
            )
            return False

        worker = ZoneWorker(
            camera_id, zones, target_fps, low_max, medium_max, high_max
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
        Restart the worker for camera_id (Task 11).

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

    def get_status(self, camera_id: uuid.UUID) -> Optional[ZoneCameraStatus]:
        """Return status for one camera, or None if no worker exists."""
        worker = self._workers.get(str(camera_id))
        return worker.get_status() if worker else None

    def get_all_statuses(self) -> List[ZoneCameraStatus]:
        """Return status snapshots for all registered workers."""
        return [w.get_status() for w in self._workers.values()]

    @property
    def active_worker_count(self) -> int:
        """Number of currently running workers."""
        return sum(1 for w in self._workers.values() if w.is_running)


# ─── Singleton ────────────────────────────────────────────────────────────────

zone_manager: ZoneManager = ZoneManager()
