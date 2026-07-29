"""
CameraManager — orchestrates all RTSP StreamWorkers.

Responsibilities:
  • Load stream-enabled cameras from the database at startup
  • Start one StreamWorker per camera
  • Flush CameraHealth records to PostgreSQL every 15 seconds
  • Expose control methods (start / stop / restart / reload) used by the API layer
  • Shut everything down cleanly on application exit
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.camera.frame_buffer import FrameBuffer
from app.camera.stream_worker import StreamWorker
from app.common.constants import (
    REDIS_CHANNEL_CAMERA_STATUS,
    REDIS_CHANNEL_CAMERA_HEALTH,
)
from app.common.enums import CameraStatus
from app.database.connection import AsyncSessionLocal
from app.events.publisher import event_publisher
from app.events.schemas import EventType, LiveEvent
from app.models.camera import Camera
from app.models.camera_health import CameraHealth

# ─── Constants ────────────────────────────────────────────────────────────────

_HEALTH_UPDATE_INTERVAL: int = 15   # seconds between DB health flushes


class CameraManager:
    """
    Application-level singleton that owns all StreamWorker instances.

    Do NOT instantiate directly — use the module-level `camera_manager` object.
    """

    def __init__(self) -> None:
        self._workers: Dict[str, StreamWorker] = {}
        self._frame_buffer: FrameBuffer = FrameBuffer()
        self._health_task: Optional[asyncio.Task] = None
        self._running: bool = False
        # Tracks the last-known status per camera to detect ONLINE/OFFLINE changes
        self._prev_statuses: Dict[str, CameraStatus] = {}

    # ─── Properties ───────────────────────────────────────────────────────────

    @property
    def frame_buffer(self) -> FrameBuffer:
        """Shared FrameBuffer — read-only for external callers."""
        return self._frame_buffer

    @property
    def active_count(self) -> int:
        """Number of workers currently managed."""
        return len(self._workers)

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def startup(self) -> None:
        """
        Called from main.py lifespan — loads cameras and starts workers.
        Non-fatal: if the DB has no cameras yet, the manager starts idle.
        """
        self._running = True
        logger.info("CameraManager starting...")
        await self._load_and_start_cameras()
        self._health_task = asyncio.create_task(
            self._health_update_loop(), name="camera-health-loop"
        )
        logger.info(
            "CameraManager ready | stream_workers={n}", n=len(self._workers)
        )

    async def shutdown(self) -> None:
        """Stop all workers and the health loop; called on app shutdown."""
        self._running = False
        logger.info("CameraManager shutting down | workers={n}", n=len(self._workers))

        # Cancel health loop first
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        # Stop all workers concurrently
        if self._workers:
            await asyncio.gather(
                *[w.stop() for w in self._workers.values()],
                return_exceptions=True,
            )
        self._workers.clear()
        await self._frame_buffer.clear()
        logger.info("CameraManager shutdown complete")

    # ─── Camera Control ───────────────────────────────────────────────────────

    async def start_camera(self, camera_id: uuid.UUID, rtsp_url: str) -> None:
        """
        Start a StreamWorker for a camera (idempotent).
        If a worker already exists and is running, this is a no-op.
        """
        key = str(camera_id)
        if key in self._workers and self._workers[key].is_running:
            logger.debug(
                "Camera already streaming | camera_id={cid}", cid=camera_id
            )
            return
        worker = StreamWorker(camera_id, rtsp_url, self._frame_buffer)
        self._workers[key] = worker
        await worker.start()

    async def stop_camera(self, camera_id: uuid.UUID) -> None:
        """Stop and remove the worker for a specific camera."""
        worker = self._workers.pop(str(camera_id), None)
        if worker:
            await worker.stop()

    async def restart_camera(self, camera_id: uuid.UUID) -> bool:
        """
        Stop the current worker and start a fresh one, re-reading the RTSP
        URL from the database (in case it was changed).

        Returns:
            True  — camera found and restarted.
            False — camera not found, inactive, or stream_enabled=False.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Camera).where(Camera.id == camera_id)
            )
            camera: Optional[Camera] = result.scalar_one_or_none()

        if camera is None:
            logger.warning(
                "Restart: camera not found | camera_id={cid}", cid=camera_id
            )
            return False

        if not camera.is_active:
            logger.warning(
                "Restart: camera is inactive | camera_id={cid}", cid=camera_id
            )
            return False

        if not camera.stream_enabled:
            logger.warning(
                "Restart: stream_enabled=False | camera_id={cid}", cid=camera_id
            )
            return False

        if not camera.rtsp_url:
            logger.warning(
                "Restart: rtsp_url is empty | camera_id={cid}", cid=camera_id
            )
            return False

        logger.info("Restarting camera stream | camera_id={cid}", cid=camera_id)
        await self.stop_camera(camera_id)
        await self.start_camera(camera_id, camera.rtsp_url)

        # Publish camera.restarted event (Task 4)
        await event_publisher.publish(
            REDIS_CHANNEL_CAMERA_STATUS,
            LiveEvent(
                event_type=EventType.CAMERA_RESTARTED,
                source="camera_manager",
                payload={
                    "camera_id": str(camera_id),
                    "camera_name": camera.camera_name,
                    "rtsp_url": camera.rtsp_url,
                },
            ),
        )
        return True

    async def reload_cameras(self) -> Dict[str, int]:
        """
        Synchronise running workers with the current database state:
          • Start workers for newly stream-enabled cameras
          • Stop workers for cameras that are deactivated / stream disabled

        Returns a summary dict: {started, stopped, total_active}
        """
        logger.info("Reloading cameras from database...")

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Camera).where(
                    Camera.is_active.is_(True),
                    Camera.stream_enabled.is_(True),
                )
            )
            db_cameras: List[Camera] = list(result.scalars().all())

        db_ids = {str(c.id) for c in db_cameras}
        current_ids = set(self._workers.keys())

        # Stop workers for cameras no longer in scope
        to_stop = current_ids - db_ids
        for cam_id_str in to_stop:
            await self.stop_camera(uuid.UUID(cam_id_str))

        # Start workers for newly eligible cameras
        started = 0
        for cam in db_cameras:
            if str(cam.id) not in self._workers:
                if cam.rtsp_url:
                    await self.start_camera(cam.id, cam.rtsp_url)
                    started += 1
                else:
                    logger.warning(
                        "Skip camera — no RTSP URL | camera_id={cid}", cid=cam.id
                    )

        summary: Dict[str, int] = {
            "started": started,
            "stopped": len(to_stop),
            "total_active": len(self._workers),
        }
        logger.info("Camera reload complete | {s}", s=summary)
        return summary

    # ─── Status Queries ───────────────────────────────────────────────────────

    def get_worker(self, camera_id: uuid.UUID) -> Optional[StreamWorker]:
        """Return the StreamWorker for a camera, or None."""
        return self._workers.get(str(camera_id))

    def get_all_statuses(self) -> List[Dict[str, Any]]:
        """Return a list of live status dicts for all managed workers."""
        return [
            {
                "camera_id": cam_id,
                "is_running": w.is_running,
                "is_connected": w.is_connected,
                "fps": w.current_fps,
                "total_frames": w.total_frames,
            }
            for cam_id, w in self._workers.items()
        ]

    async def get_latest_frame(self, camera_id: uuid.UUID) -> Optional[Any]:
        """
        Return the latest FrameEntry for a camera, or None if unavailable.

        This is the ONLY method AI modules (Phase 3+) should call to access frames.
        Direct access to frame_buffer from outside this class is discouraged.

        Returns:
            FrameEntry  — dataclass with latest_frame, timestamp, fps, frame_number.
            None        — no frame available (worker not started or not yet connected).
        """
        return await self._frame_buffer.get(camera_id)

    # ─── Health Flush Loop ────────────────────────────────────────────────────

    async def _health_update_loop(self) -> None:
        """
        Background task: write CameraHealth rows and update Camera status
        every _HEALTH_UPDATE_INTERVAL seconds.
        """
        while self._running:
            try:
                await asyncio.sleep(_HEALTH_UPDATE_INTERVAL)
                if self._workers:
                    await self._flush_health_to_db()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "Health update loop error | error={err}", err=str(exc)
                )

    async def _flush_health_to_db(self) -> None:
        """
        Write one CameraHealth snapshot per active worker and update
        Camera.status / Camera.last_frame_time / Camera.last_health_check.
        """
        frame_entries = await self._frame_buffer.all_entries()
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                for cam_id_str, worker in list(self._workers.items()):
                    try:
                        cam_uuid = uuid.UUID(cam_id_str)
                        entry = frame_entries.get(cam_id_str)
                        status = (
                            CameraStatus.ONLINE
                            if worker.is_connected
                            else CameraStatus.OFFLINE
                        )
                        fps = worker.current_fps
                        last_frame_time = entry.timestamp if entry else None

                        # ── CameraHealth snapshot row ─────────────────────────
                        health = CameraHealth(
                            camera_id=cam_uuid,
                            fps=fps,
                            recorded_at=now,
                            error_message=(
                                None
                                if worker.is_connected
                                else "Stream disconnected"
                            ),
                        )
                        session.add(health)

                        # ── Update live Camera state ───────────────────────────
                        await session.execute(
                            update(Camera)
                            .where(Camera.id == cam_uuid)
                            .values(
                                status=status,
                                last_frame_time=last_frame_time,
                                last_health_check=now,
                            )
                        )

                        # ── Detect status change → publish connected/disconnected ──
                        prev = self._prev_statuses.get(cam_id_str)
                        if prev != status:
                            self._prev_statuses[cam_id_str] = status
                            evt_type = (
                                EventType.CAMERA_CONNECTED
                                if status == CameraStatus.ONLINE
                                else EventType.CAMERA_DISCONNECTED
                            )
                            await event_publisher.publish(
                                REDIS_CHANNEL_CAMERA_STATUS,
                                LiveEvent(
                                    event_type=evt_type,
                                    source="camera_manager",
                                    payload={
                                        "camera_id": str(cam_uuid),
                                        "status": status.value,
                                        "fps": fps,
                                    },
                                ),
                            )

                        # ── Always publish health update ──────────────────────
                        await event_publisher.publish(
                            REDIS_CHANNEL_CAMERA_HEALTH,
                            LiveEvent(
                                event_type=EventType.CAMERA_HEALTH_UPDATED,
                                source="camera_manager",
                                payload={
                                    "camera_id": str(cam_uuid),
                                    "status": status.value,
                                    "fps": fps,
                                    "last_frame_time": (
                                        last_frame_time.isoformat()
                                        if last_frame_time
                                        else None
                                    ),
                                },
                            ),
                        )

                        logger.debug(
                            "Health flushed | camera_id={cid} | "
                            "status={s} | fps={fps}",
                            cid=cam_uuid,
                            s=status,
                            fps=fps,
                        )

                    except Exception as exc:
                        logger.error(
                            "Health flush error | camera_id={cid} | error={err}",
                            cid=cam_id_str,
                            err=str(exc),
                        )

    # ─── Private Helpers ──────────────────────────────────────────────────────

    async def _load_and_start_cameras(self) -> None:
        """Query DB for active stream-enabled cameras and start their workers."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Camera).where(
                        Camera.is_active.is_(True),
                        Camera.stream_enabled.is_(True),
                    )
                )
                cameras: List[Camera] = list(result.scalars().all())

            logger.info(
                "Found {n} stream-enabled cameras in database", n=len(cameras)
            )
            for cam in cameras:
                if cam.rtsp_url:
                    await self.start_camera(cam.id, cam.rtsp_url)
                else:
                    logger.warning(
                        "Camera skipped — rtsp_url is empty | camera_id={cid}",
                        cid=cam.id,
                    )
        except Exception as exc:
            logger.error(
                "Failed to load cameras from DB | error={err}", err=str(exc)
            )


# ─── Singleton ────────────────────────────────────────────────────────────────

camera_manager: CameraManager = CameraManager()
