"""
QueueWorker — per-camera queue monitoring asyncio.Task (Tasks 4, 8, 9, 10, 11).

═══════════════════════════════════════════════════════════════════════
Worker lifecycle
═══════════════════════════════════════════════════════════════════════

    start()   → creates and schedules an asyncio.Task (_run_loop)
    stop()    → cancels the task and waits up to 5 s
    restart() → stop() then start()

The worker never crashes FastAPI:
    • Every exception inside _run_loop is caught, logged, and the loop
      continues automatically (Task 11 — automatic recovery).
    • asyncio.CancelledError is re-raised so stop() works cleanly.

═══════════════════════════════════════════════════════════════════════
Per-frame pipeline (Task 4)
═══════════════════════════════════════════════════════════════════════

    1. camera_manager.get_latest_frame(camera_id)   [async]
    2. Skip if frame_number unchanged               [no GPU wasted]
    3. asyncio.to_thread(analyzer.analyze, frame)   [blocking → thread]
    4. Update internal metrics
    5. Log FPS every 5 s
    6. Publish to Redis if metrics changed          [change-only]

═══════════════════════════════════════════════════════════════════════
Redis event format (Task 6)
═══════════════════════════════════════════════════════════════════════

Published to channel:queue.status ONLY when people_inside_queue
or queue_status changes:

    {
        "camera_id":          "...",
        "people_inside_queue": 18,
        "queue_length":        18,
        "queue_status":        "MEDIUM",
        "timestamp":           "2026-07-25T00:00:00+00:00"
    }

═══════════════════════════════════════════════════════════════════════
Performance (Task 10)
═══════════════════════════════════════════════════════════════════════

• Default target: 5 FPS (queue state changes slowly, 5 FPS is ample)
• Frame deduplication: skips if frame_number == last_frame_number
• analyzer.analyze() runs in asyncio.to_thread() — event loop not blocked
• Shared YOLO model is reused (never reloaded)
• Supports 13 cameras simultaneously (independent workers)
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from loguru import logger

from app.camera.camera_manager import camera_manager
from app.common.constants import REDIS_CHANNEL_QUEUE_STATUS
from app.events.publisher import event_publisher
from app.events.schemas import LiveEvent
from app.queue_management.analyzer import QueueAnalyzer, DEFAULT_LOW_MAX, DEFAULT_MEDIUM_MAX
from app.queue_management.roi import QueueROI
from app.queue_management.schemas import QueueStatus

_EVENT_TYPE_QUEUE: str = "queue.status"
_DEFAULT_TARGET_FPS: int = 5   # Queue state changes slowly — 5 FPS is sufficient


class QueueWorker:
    """
    Queue monitoring worker for one camera.

    Owns a QueueAnalyzer (which owns a QueueROI).
    Runs as an asyncio.Task — one worker per camera.

    Lifecycle:
        worker = QueueWorker(camera_id, roi)
        await worker.start()
        # ... runs in background indefinitely ...
        await worker.stop()
    """

    def __init__(
        self,
        camera_id: uuid.UUID,
        roi: QueueROI,
        target_fps: int = _DEFAULT_TARGET_FPS,
        low_max: int = DEFAULT_LOW_MAX,
        medium_max: int = DEFAULT_MEDIUM_MAX,
        direction: str = "UP",
        stabilization_sec: float = 3.0,
    ) -> None:
        self._camera_id = camera_id
        self._cam_id_str = str(camera_id)
        self._roi = roi
        self._target_interval: float = 1.0 / max(1, target_fps)
        self._low_max = low_max
        self._medium_max = medium_max
        self._direction = direction
        self._stabilization_sec = stabilization_sec

        # QueueAnalyzer is now stateful (holds ByteTrack + motion history)
        self._analyzer = QueueAnalyzer(
            roi, low_max, medium_max,
            direction=direction,
            stabilization_sec=stabilization_sec,
        )

        # Level 1 — Occupancy
        self._people_inside: int = 0
        self._queue_length: int = 0
        self._queue_status: str = "EMPTY"

        # Level 2 — Movement
        self._movement_px: float = 0.0
        self._forward_movers: int = 0
        self._tracked_people: int = 0
        self._progress_ratio: float = 0.0

        # Level 3 — Speed
        self._speed_px_per_sec: float = 0.0

        # Level 4 — Health
        self._queue_health: str = "UNKNOWN"
        self._pending_health: str = "UNKNOWN"

        # Level 5 — Stagnation
        self._stagnation_seconds: float = 0.0
        self._stagnation_label: str = "OK"

        # Task state
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._last_frame_number: int = -1

        # FPS measurement (5-second rolling window)
        self._proc_count: int = 0
        self._fps_window_start: float = time.monotonic()
        self._current_fps: float = 0.0

        # Change detection — only publish when values differ from last publish
        self._last_pub_count: int = -1
        self._last_pub_status: str = ""
        self._last_pub_health: str = ""

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """True while the asyncio.Task is alive and not cancelled."""
        return (
            self._running
            and self._task is not None
            and not self._task.done()
        )

    @property
    def roi(self) -> QueueROI:
        """The ROI this worker monitors."""
        return self._roi

    @property
    def direction(self) -> str:
        """Queue movement direction."""
        return self._direction

    @property
    def stabilization_sec(self) -> float:
        """Seconds before counts stabilize."""
        return self._stabilization_sec

    @property
    def target_fps(self) -> int:
        """Target inference rate in FPS."""
        return round(1.0 / self._target_interval)

    @property
    def low_max(self) -> int:
        """Upper bound for LOW queue status."""
        return self._low_max

    @property
    def medium_max(self) -> int:
        """Upper bound for MEDIUM queue status."""
        return self._medium_max

    async def start(self) -> None:
        """Spawn the background monitoring task (idempotent)."""
        if self.is_running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(),
            name=f"queue-worker-{self._cam_id_str}",
        )
        logger.info(
            "QueueWorker started | camera_id={cid} | "
            "roi={roi} | target_fps={fps}",
            cid=self._cam_id_str,
            roi=repr(self._roi),
            fps=round(1.0 / self._target_interval),
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
            "QueueWorker stopped | camera_id={cid} | "
            "final: people={p} | status={s}",
            cid=self._cam_id_str,
            p=self._people_inside,
            s=self._queue_status,
        )

    async def restart(self) -> None:
        """Stop then start — useful for ROI reconfiguration."""
        await self.stop()
        await self.start()
        logger.info(
            "QueueWorker restarted | camera_id={cid}", cid=self._cam_id_str
        )

    def get_status(self) -> QueueStatus:
        """Return a live snapshot of all 5-level queue metrics."""
        return QueueStatus(
            camera_id=self._cam_id_str,
            worker_running=self.is_running,
            # Level 1
            people_inside_queue=self._people_inside,
            queue_length=self._queue_length,
            queue_status=self._queue_status,
            # Level 2
            movement_px=self._movement_px,
            forward_movers=self._forward_movers,
            tracked_people=self._tracked_people,
            progress_ratio=self._progress_ratio,
            # Level 3
            speed_px_per_sec=self._speed_px_per_sec,
            # Level 4  (pending_health is internal only, not in public schema)
            queue_health=self._queue_health,
            # Level 5
            stagnation_seconds=self._stagnation_seconds,
            stagnation_label=self._stagnation_label,
            # Meta
            queue_direction=self._direction,
            fps=round(self._current_fps, 1),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        """
        Outer loop — runs until stop() is called.
        Catches and logs all exceptions; never exits on error (Task 11).
        """
        while self._running:
            t_iter_start = time.monotonic()
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise  # Let stop() handle it
            except Exception as exc:
                logger.error(
                    "QueueWorker unexpected error | camera_id={cid} | {err}",
                    cid=self._cam_id_str,
                    err=str(exc),
                    exc_info=True,
                )
            # Sleep for the remainder of the target interval
            elapsed = time.monotonic() - t_iter_start
            await asyncio.sleep(max(0.0, self._target_interval - elapsed))

    async def _run_once(self) -> None:
        """One complete iteration of the queue monitoring pipeline."""

        # ── 1. Get latest frame from CameraManager ────────────────────────────
        frame_entry = await camera_manager.get_latest_frame(self._camera_id)
        if frame_entry is None or frame_entry.latest_frame is None:
            # Camera not streaming — wait and retry next iteration
            await asyncio.sleep(0.1)
            return

        # ── 2. Frame deduplication ────────────────────────────────────────────
        # frame_number increments for every new frame captured by StreamWorker.
        # If the number hasn't changed, the camera didn't produce a new frame —
        # skip inference to avoid redundant GPU work.
        if frame_entry.frame_number == self._last_frame_number:
            return
        self._last_frame_number = frame_entry.frame_number
        frame = frame_entry.latest_frame

        # ── 3. Run analyzer in thread executor ────────────────────────────────
        # QueueAnalyzer.analyze() is synchronous (YOLO + numpy).
        # asyncio.to_thread() offloads it to the default executor so the
        # event loop stays responsive for API requests and WebSocket traffic.
        metrics = await asyncio.to_thread(self._analyzer.analyze, frame)

        # ── 4. Update internal state — all 5 levels ───────────────────────────
        self._people_inside      = metrics["people_inside_queue"]
        self._queue_length       = metrics["queue_length"]
        self._queue_status       = metrics["queue_status"]
        self._movement_px        = metrics["movement_px"]
        self._forward_movers     = metrics["forward_movers"]
        self._tracked_people     = metrics["tracked_people"]
        self._progress_ratio     = metrics["progress_ratio"]
        self._speed_px_per_sec   = metrics["speed_px_per_sec"]
        self._queue_health       = metrics["queue_health"]
        self._pending_health     = metrics["_pending_health"]  # internal only
        self._stagnation_seconds = metrics["stagnation_seconds"]
        self._stagnation_label   = metrics["stagnation_label"]

        logger.debug(
            "Queue frame | camera={cid} | people={p} | status={s} "
            "| health={h} | speed={spd:.1f}px/s | stag={stag:.0f}s | infer={t:.1f}ms",
            cid=self._cam_id_str,
            p=self._people_inside,
            s=self._queue_status,
            h=self._queue_health,
            spd=self._speed_px_per_sec,
            stag=self._stagnation_seconds,
            t=metrics["inference_ms"],
        )

        # ── 5. FPS measurement (log every 5 seconds) ──────────────────────────
        self._proc_count += 1
        now = time.monotonic()
        window = now - self._fps_window_start
        if window >= 5.0:
            self._current_fps = self._proc_count / window
            logger.info(
                "QueueWorker FPS | camera={cid} | fps={fps:.1f} | "
                "people={p} | status={s}",
                cid=self._cam_id_str,
                fps=self._current_fps,
                p=self._people_inside,
                s=self._queue_status,
            )
            self._proc_count = 0
            self._fps_window_start = now

        # ── 6. Publish to Redis if metrics changed ────────────────────────────
        if (
            self._people_inside != self._last_pub_count
            or self._queue_status != self._last_pub_status
            or self._queue_health != self._last_pub_health
        ):
            await self._publish()
            self._last_pub_count = self._people_inside
            self._last_pub_status = self._queue_status
            self._last_pub_health = self._queue_health

    # ── Redis publishing ──────────────────────────────────────────────────────

    async def _publish(self) -> None:
        """
        Publish current queue metrics to Redis channel:queue.status.

        Called only when people_inside_queue or queue_status changes.
        Never publishes on every frame.

        Payload matches the user-specified format exactly:
            {
                "camera_id":           "...",
                "people_inside_queue": 18,
                "queue_length":        18,
                "queue_status":        "MEDIUM",
                "timestamp":           "..."
            }
        """
        await event_publisher.publish(
            REDIS_CHANNEL_QUEUE_STATUS,
            LiveEvent(
                event_type=_EVENT_TYPE_QUEUE,
                source="queue_worker",
                payload={
                    "camera_id":           self._cam_id_str,
                    "people_inside_queue": self._people_inside,
                    "queue_length":        self._queue_length,
                    "queue_status":        self._queue_status,
                    "movement_px":         self._movement_px,
                    "forward_movers":      self._forward_movers,
                    "tracked_people":      self._tracked_people,
                    "progress_ratio":      self._progress_ratio,
                    "speed_px_per_sec":    self._speed_px_per_sec,
                    "queue_health":        self._queue_health,
                    # pending_health omitted from publish (internal only)
                    "stagnation_seconds":  self._stagnation_seconds,
                    "stagnation_label":    self._stagnation_label,
                    "queue_direction":     self._direction,
                    "timestamp":           datetime.now(timezone.utc).isoformat(),
                },
            ),
        )
        logger.debug(
            "Queue published | camera={cid} | people={p} | status={s}",
            cid=self._cam_id_str,
            p=self._people_inside,
            s=self._queue_status,
        )
