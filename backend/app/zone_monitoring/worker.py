"""
ZoneWorker — per-camera zone monitoring asyncio.Task (Tasks 7, 9, 11, 12, 13, 14).

═══════════════════════════════════════════════════════════════════════
Worker lifecycle (Task 11)
═══════════════════════════════════════════════════════════════════════

    start()   → creates and schedules an asyncio.Task (_run_loop)
    stop()    → cancels the task, waits up to 5 seconds
    restart() → stop() then start()

The worker never crashes FastAPI:
    • Every exception inside _run_loop is caught, logged, and the loop
      continues automatically (automatic recovery — Task 14).
    • asyncio.CancelledError is re-raised so stop() works cleanly.

═══════════════════════════════════════════════════════════════════════
Per-frame pipeline (Task 7)
═══════════════════════════════════════════════════════════════════════

    1.  camera_manager.get_latest_frame(camera_id)    [async]
    2.  Skip if frame_number unchanged                [no GPU wasted]
    3.  asyncio.to_thread(analyzer.analyze, frame)    [blocking → thread]
    4.  Update internal zone metrics
    5.  Log FPS every 5 s                             [Task 12]
    6.  Publish to Redis if any zone changed          [Task 9]

═══════════════════════════════════════════════════════════════════════
Change detection for Redis (Task 9)
═══════════════════════════════════════════════════════════════════════

The worker compares the current snapshot against the last published one.
A "change" is any difference in people_count OR status for any zone.
If nothing changed, Redis is NOT published (never publish every frame).

═══════════════════════════════════════════════════════════════════════
Redis event format (Task 9)
═══════════════════════════════════════════════════════════════════════

Published to channel:zone.status on change:

    {
        "camera_id": "...",
        "zones": [
            {"zone_id": "A", "people_count": 12, "status": "LOW"},
            {"zone_id": "B", "people_count": 37, "status": "HIGH"}
        ],
        "timestamp": "2026-07-25T00:00:00+00:00"
    }

═══════════════════════════════════════════════════════════════════════
Performance (Task 13)
═══════════════════════════════════════════════════════════════════════

• Default target: 5 FPS (zone occupancy changes slowly)
• Frame deduplication: skips if frame_number == last_frame_number
• analyzer.analyze() runs in asyncio.to_thread() — event loop never blocked
• Shared YOLO model is reused via detector.detect() — never reloaded
• Supports N cameras × M zones simultaneously (independent workers)
• No unnecessary dict/list allocations in the hot path
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from app.camera.camera_manager import camera_manager
from app.common.constants import REDIS_CHANNEL_ZONE_STATUS
from app.events.publisher import event_publisher
from app.events.schemas import LiveEvent
from app.zone_monitoring.analyzer import (
    ZoneAnalyzer,
    DEFAULT_LOW_MAX,
    DEFAULT_MEDIUM_MAX,
    DEFAULT_HIGH_MAX,
)
from app.zone_monitoring.schemas import ZoneCameraStatus, ZoneMetrics
from app.zone_monitoring.zone import Zone

_EVENT_TYPE_ZONE: str = "zone.status"
_DEFAULT_TARGET_FPS: int = 5  # 5 FPS is sufficient for zone monitoring


class ZoneWorker:
    """
    Zone monitoring worker for one camera.

    Owns a ZoneAnalyzer (which owns the Zone list).
    Runs as an asyncio.Task — one worker per camera.

    Lifecycle:
        worker = ZoneWorker(camera_id, zones)
        await worker.start()
        # ... runs in background indefinitely ...
        await worker.stop()
    """

    def __init__(
        self,
        camera_id: uuid.UUID,
        zones: List[Zone],
        target_fps: int = _DEFAULT_TARGET_FPS,
        low_max: int = DEFAULT_LOW_MAX,
        medium_max: int = DEFAULT_MEDIUM_MAX,
        high_max: int = DEFAULT_HIGH_MAX,
    ) -> None:
        self._camera_id = camera_id
        self._cam_id_str = str(camera_id)
        self._zones = zones
        self._target_interval: float = 1.0 / max(1, target_fps)

        self._analyzer = ZoneAnalyzer(
            self._cam_id_str, zones, low_max, medium_max, high_max
        )

        # Latest zone metrics — list of dicts from analyzer.analyze()
        self._latest_zones: List[Dict[str, Any]] = [
            {
                "zone_id": z.zone_id,
                "zone_name": z.zone_name,
                "people_count": 0,
                "density": 0.0,
                "status": "EMPTY",
            }
            for z in zones
        ]

        # Task state
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._last_frame_number: int = -1

        # FPS measurement (5-second rolling window)
        self._proc_count: int = 0
        self._fps_window_start: float = time.monotonic()
        self._current_fps: float = 0.0

        # Change fingerprint: (zone_id, people_count, status) tuples
        # Compared after each frame to decide whether to publish
        self._last_pub_fingerprint: tuple = ()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """True while the asyncio.Task is alive and not cancelled."""
        return (
            self._running
            and self._task is not None
            and not self._task.done()
        )

    async def start(self) -> None:
        """Spawn the background monitoring task (idempotent)."""
        if self.is_running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(),
            name=f"zone-worker-{self._cam_id_str}",
        )
        logger.info(
            "ZoneWorker started | camera_id={cid} | zones={zids}",
            cid=self._cam_id_str,
            zids=[z.zone_id for z in self._zones],
        )

    async def stop(self) -> None:
        """Stop the worker and wait for clean shutdown (max 5 s)."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info(
            "ZoneWorker stopped | camera_id={cid}", cid=self._cam_id_str
        )

    async def restart(self) -> None:
        """Stop then start — useful for zone reconfiguration (Task 11)."""
        await self.stop()
        await self.start()
        logger.info(
            "ZoneWorker restarted | camera_id={cid}", cid=self._cam_id_str
        )

    def get_status(self) -> ZoneCameraStatus:
        """Return a live snapshot of all zone metrics and worker state."""
        return ZoneCameraStatus(
            camera_id=self._cam_id_str,
            worker_running=self.is_running,
            zones=[
                ZoneMetrics(
                    zone_id=z["zone_id"],
                    zone_name=z["zone_name"],
                    people_count=z["people_count"],
                    density=z["density"],
                    status=z["status"],
                )
                for z in self._latest_zones
            ],
            fps=round(self._current_fps, 1),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        """
        Outer loop — runs until stop() is called.
        Catches and logs all exceptions; never exits on error (Task 14).
        """
        while self._running:
            t_iter_start = time.monotonic()
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise  # Let stop() handle it
            except Exception as exc:
                logger.error(
                    "ZoneWorker unexpected error | camera_id={cid} | {err}",
                    cid=self._cam_id_str,
                    err=str(exc),
                    exc_info=True,
                )
            elapsed = time.monotonic() - t_iter_start
            await asyncio.sleep(max(0.0, self._target_interval - elapsed))

    async def _run_once(self) -> None:
        """One complete iteration of the zone monitoring pipeline."""

        # ── 1. Get latest frame from CameraManager ────────────────────────────
        frame_entry = await camera_manager.get_latest_frame(self._camera_id)
        if frame_entry is None or frame_entry.latest_frame is None:
            await asyncio.sleep(0.1)
            return

        # ── 2. Frame deduplication (Task 7) ───────────────────────────────────
        # frame_number is a monotonic counter in FrameBuffer. If unchanged,
        # the camera produced no new frame → skip redundant GPU work.
        if frame_entry.frame_number == self._last_frame_number:
            return
        self._last_frame_number = frame_entry.frame_number
        frame = frame_entry.latest_frame

        # ── 3. Analyze zones in thread executor ───────────────────────────────
        # ZoneAnalyzer.analyze() is synchronous (YOLO + numpy).
        # asyncio.to_thread() offloads it so the event loop stays responsive.
        result = await asyncio.to_thread(self._analyzer.analyze, frame)

        self._latest_zones = result["zones"]

        logger.debug(
            "Zone frame | camera={cid} | zones={zs} | time={t:.1f}ms",
            cid=self._cam_id_str,
            zs=[
                f"{z['zone_id']}:{z['people_count']}({z['status']})"
                for z in self._latest_zones
            ],
            t=result["processing_time_ms"],
        )

        # ── 4. FPS measurement (log every 5 seconds, Task 12) ─────────────────
        self._proc_count += 1
        now = time.monotonic()
        window = now - self._fps_window_start
        if window >= 5.0:
            self._current_fps = self._proc_count / window
            logger.info(
                "ZoneWorker FPS | camera={cid} | fps={fps:.1f} | "
                "zones={zs}",
                cid=self._cam_id_str,
                fps=self._current_fps,
                zs=[
                    f"{z['zone_id']}:{z['people_count']}({z['status']})"
                    for z in self._latest_zones
                ],
            )
            self._proc_count = 0
            self._fps_window_start = now

        # ── 5. Publish if any zone changed (Task 9) ───────────────────────────
        new_fingerprint = tuple(
            (z["zone_id"], z["people_count"], z["status"])
            for z in self._latest_zones
        )
        if new_fingerprint != self._last_pub_fingerprint:
            await self._publish(result["timestamp"])
            self._last_pub_fingerprint = new_fingerprint

    # ── Redis publishing ──────────────────────────────────────────────────────

    async def _publish(self, timestamp: str) -> None:
        """
        Publish zone metrics to Redis channel:zone.status.

        Called only when at least one zone's people_count or status changed.
        Never publishes on every frame (Task 9).

        Payload format (Task 9):
            {
                "camera_id": "...",
                "zones": [
                    {"zone_id": "A", "people_count": 12, "status": "LOW"},
                    ...
                ],
                "timestamp": "..."
            }
        """
        await event_publisher.publish(
            REDIS_CHANNEL_ZONE_STATUS,
            LiveEvent(
                event_type=_EVENT_TYPE_ZONE,
                source="zone_worker",
                payload={
                    "camera_id": self._cam_id_str,
                    "zones": [
                        {
                            "zone_id":      z["zone_id"],
                            "people_count": z["people_count"],
                            "status":       z["status"],
                        }
                        for z in self._latest_zones
                    ],
                    "timestamp": timestamp,
                },
            ),
        )
        logger.debug(
            "Zone published | camera={cid} | zones={zs}",
            cid=self._cam_id_str,
            zs=[
                f"{z['zone_id']}:{z['people_count']}({z['status']})"
                for z in self._latest_zones
            ],
        )
