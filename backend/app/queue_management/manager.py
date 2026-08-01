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
    • Persists worker configs to Redis so they survive server restarts

═══════════════════════════════════════════════════════════════════════
REST API integration
═══════════════════════════════════════════════════════════════════════

    POST /queue/start/{camera_id}     → queue_manager.start_worker()
    POST /queue/stop/{camera_id}      → queue_manager.stop_worker()
    GET  /queue/status                → queue_manager.get_all_statuses()
    GET  /queue/status/{camera_id}    → queue_manager.get_status()
"""
import json
import uuid
from typing import Dict, List, Optional

from loguru import logger

from app.queue_management.analyzer import DEFAULT_LOW_MAX, DEFAULT_MEDIUM_MAX
from app.queue_management.roi import QueueROI
from app.queue_management.schemas import QueueStatus
from app.queue_management.worker import QueueWorker, _DEFAULT_TARGET_FPS

# Redis key that stores all active queue worker configs as a JSON dict
_REDIS_KEY = "queue_manager:workers"


class QueueManager:
    """
    Global registry for QueueWorker instances.

    One worker per camera. Thread-safe for asyncio (all operations are
    awaitable and run in the single-threaded event loop).

    Worker configs are persisted to Redis on every start_worker() call
    so that restore_from_redis() can rebuild all workers on next startup,
    even when the database is in DEGRADED mode.
    """

    def __init__(self) -> None:
        self._workers: Dict[str, QueueWorker] = {}

    # ── Redis persistence ─────────────────────────────────────────────────────

    async def _save_to_redis(self) -> None:
        """Persist all current running worker configs to Redis."""
        try:
            from app.utils.redis_manager import redis_manager
            if not redis_manager.is_connected:
                return
            payload = {}
            for cam_id_str, worker in self._workers.items():
                if worker.is_running:
                    payload[cam_id_str] = {
                        "x1": worker.roi.x1,
                        "y1": worker.roi.y1,
                        "x2": worker.roi.x2,
                        "y2": worker.roi.y2,
                        "direction": worker.direction,
                        "stabilization_sec": worker.stabilization_sec,
                        "target_fps": worker.target_fps,
                        "low_max": worker.low_max,
                        "medium_max": worker.medium_max,
                    }
            client = redis_manager.client
            await client.set(_REDIS_KEY, json.dumps(payload))
            logger.debug("QueueManager: saved {n} worker(s) to Redis", n=len(payload))
        except Exception as exc:
            logger.debug("QueueManager: Redis save skipped | err={e}", e=exc)

    async def restore_from_redis(self) -> int:
        """
        Re-start all queue workers that were saved to Redis on a previous run.
        Called once during application startup (after Redis connects).

        Returns:
            Number of workers successfully restored.
        """
        try:
            from app.utils.redis_manager import redis_manager
            if not redis_manager.is_connected:
                logger.debug("QueueManager: Redis not connected, skipping restore")
                return 0
            client = redis_manager.client
            raw = await client.get(_REDIS_KEY)
            if not raw:
                logger.info("QueueManager: no saved worker configs found in Redis")
                return 0

            payload: dict = json.loads(raw)
            restored = 0
            for cam_id_str, cfg in payload.items():
                try:
                    cam_id = uuid.UUID(cam_id_str)
                    roi = QueueROI(
                        x1=cfg["x1"], y1=cfg["y1"],
                        x2=cfg["x2"], y2=cfg["y2"],
                    )
                    started = await self.start_worker(
                        camera_id=cam_id,
                        roi=roi,
                        direction=cfg.get("direction", "DOWN"),
                        stabilization_sec=cfg.get("stabilization_sec", 3.0),
                        target_fps=cfg.get("target_fps", _DEFAULT_TARGET_FPS),
                        low_max=cfg.get("low_max", DEFAULT_LOW_MAX),
                        medium_max=cfg.get("medium_max", DEFAULT_MEDIUM_MAX),
                    )
                    if started:
                        restored += 1
                        logger.info(
                            "QueueManager: restored worker from Redis | camera={cid}",
                            cid=cam_id_str,
                        )
                except Exception as cam_exc:
                    logger.warning(
                        "QueueManager: failed to restore worker | camera={cid} | err={e}",
                        cid=cam_id_str, e=cam_exc,
                    )
            return restored
        except Exception as exc:
            logger.warning("QueueManager: Redis restore failed | err={e}", e=exc)
            return 0

    async def clear_redis(self) -> None:
        """Remove all saved worker configs from Redis."""
        try:
            from app.utils.redis_manager import redis_manager
            if redis_manager.is_connected:
                client = redis_manager.client
                await client.delete(_REDIS_KEY)
        except Exception:
            pass

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

        # Persist config so it survives restarts
        await self._save_to_redis()
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
        # Update Redis — remove stopped worker
        await self._save_to_redis()
        return True

    async def restart_worker(self, camera_id: uuid.UUID) -> bool:
        """
        Restart the worker for camera_id.

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
