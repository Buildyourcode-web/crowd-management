"""
PersonCounterWorker — Phase 4 AI pipeline (Tasks 6, 7, 10, 11, 12, 13).

═══════════════════════════════════════════════════════════════════════
How the worker operates
═══════════════════════════════════════════════════════════════════════

One worker runs per camera as an asyncio.Task.

Each iteration of the main loop:
    1. Fetch FrameEntry from CameraManager (async, non-blocking)
    2. Skip the iteration if frame_number hasn't changed
       (avoids redundant GPU inference on duplicate frames)
    3. Run PersonTracker.update(frame) in a thread executor
       (detection + ByteTrack are synchronous/blocking)
    4. For every tracked person:
         • If previous centroid is known, call CountingLine.check_crossing()
         • "entry" → PersonCounter.add_entry()  + log
         • "exit"  → PersonCounter.add_exit()   + log
         • Store new centroid as previous for next frame
    5. Remove track IDs that are no longer active (person left frame)
    6. Measure and log FPS every 5 seconds
    7. If entry_count or exit_count changed since last publish →
       publish {camera_id, entry, exit, current, timestamp} to Redis

═══════════════════════════════════════════════════════════════════════
How ByteTrack is used
═══════════════════════════════════════════════════════════════════════

Each worker owns a PersonTracker which owns a standalone BYTETracker.
The shared YOLO model (ModelManager singleton) is called with
classes=[0] (person only). Detection results are passed directly to
the per-camera BYTETracker — no model state is shared between cameras.

Thread management: detection + tracking run inside asyncio.to_thread()
so the event loop is never blocked. Each camera's tracker is called
from exactly one thread at a time (the thread executor slot for that
task iteration), so no locking is needed inside PersonTracker.

═══════════════════════════════════════════════════════════════════════
How line crossing works
═══════════════════════════════════════════════════════════════════════

self._prev_positions: Dict[track_id → (cx, cy)] stores the centroid of
each visible track from the previous frame.

When a track reappears in the current frame:
    crossing = counting_line.check_crossing(prev_cx, prev_cy, cx, cy)

The cross-product sign change determines direction:
    Horizontal line: top→bottom = "entry",  bottom→top = "exit"
    Vertical line:   left→right = "entry",  right→left = "exit"

Anti-double-count guarantee:
    A crossing fires ONLY when the centroid crosses from one side to the
    other. A person standing on the line or moving parallel to it never
    triggers a count. The sign-change check is atomic per frame — one
    crossing = one event.

═══════════════════════════════════════════════════════════════════════
How occupancy is calculated
═══════════════════════════════════════════════════════════════════════

    current_occupancy = max(0, entry_count − exit_count)

Published to Redis only when entry_count or exit_count changes.
The max(0, ...) clamp prevents negative values from sensor drift.

═══════════════════════════════════════════════════════════════════════
Error handling (Task 12)
═══════════════════════════════════════════════════════════════════════

Every exception inside the main loop is caught, logged, and the loop
continues. The worker NEVER crashes FastAPI. Specific resilience:
    • Camera unavailable → sleep 0.1 s, retry
    • Frame empty        → skip iteration
    • Tracker failure    → returns [], crossing logic skipped
    • YOLO error         → caught inside PersonTracker, returns []
    • Redis publish fail → caught inside EventPublisher, logged
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from loguru import logger

from app.camera.camera_manager import camera_manager
from app.common.constants import REDIS_CHANNEL_PERSON_COUNT
from app.database.connection import AsyncSessionLocal
from app.events.publisher import event_publisher
from app.events.schemas import LiveEvent
from app.models.count import EntryExitCount
from app.person_counter.counter import PersonCounter
from app.person_counter.roi import CountingLine, TriggerZone
from app.person_counter.schemas import PersonCountStatus
from app.person_counter.tracker import PersonTracker, TrackedPerson

# Redis key for persisting counter configs
_REDIS_CONFIG_KEY = "person_counter:configs"

# Fake event type string for person count events
_EVENT_TYPE_PERSON_COUNT: str = "person.count"

# Default target inference rate
_DEFAULT_TARGET_FPS: int = 10


# ─── Worker ───────────────────────────────────────────────────────────────────


class PersonCounterWorker:
    """
    Entry/Exit counting worker for one camera.

    Lifecycle:
        worker = PersonCounterWorker(camera_id, counting_line)
        await worker.start()    # spawns asyncio.Task
        await worker.stop()     # cancels task, waits for cleanup
        status = worker.get_status()
    """

    def __init__(
        self,
        camera_id: uuid.UUID,
        counting_line: CountingLine,
        target_fps: int = _DEFAULT_TARGET_FPS,
    ) -> None:
        self._camera_id = camera_id
        self._cam_id_str = str(camera_id)
        self._line = counting_line
        self._target_interval: float = 1.0 / max(1, target_fps)

        # Auto-create a TriggerZone from the counting line
        # Zone = full-width band of 160px centered on the line
        # This is the ZONE used for counting: person enters zone → counted once
        self._zone = TriggerZone.for_horizontal_band(
            frame_width=counting_line.end_x,
            y_center=(counting_line.start_y + counting_line.end_y) / 2,
            band_height=160.0,   # 160px tall trigger strip
        )

        # Core components (owned by this worker)
        self._counter = PersonCounter()
        self._tracker = PersonTracker(frame_rate=target_fps)

        # Line-crossing counting state:
        # _prev_positions : last known centroid per track_id (for crossing check)
        # _counted_ids    : track_ids that have crossed the line — NEVER cleared
        #                   on transient track loss (Phase 1 fix). Only grows.
        self._prev_positions: Dict[int, Tuple[float, float]] = {}
        self._counted_ids: Dict[int, float] = {}


        # Latest tracked persons for stream bounding box overlay
        self._latest_tracked: List[TrackedPerson] = []

        self._last_frame_number: int = -1

        # Task lifecycle
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

        # FPS measurement (5-second rolling window)
        self._proc_frame_count: int = 0
        self._fps_window_start: float = time.monotonic()
        self._current_fps: float = 0.0

        # Change detection for Redis publish
        self._last_pub_entry: int = -1
        self._last_pub_exit: int = -1

    def update_line(self, counting_line: CountingLine) -> None:
        """Update counting line dynamically on the live worker without restarting task."""
        self._line = counting_line
        self._zone = TriggerZone.for_horizontal_band(
            frame_width=max(counting_line.start_x, counting_line.end_x, 1920.0),
            y_center=(counting_line.start_y + counting_line.end_y) / 2.0,
            band_height=160.0,
        )
        logger.info(
            "PersonCounter line dynamically updated | camera_id={cid} | "
            "line=({sx:.0f},{sy:.0f})→({ex:.0f},{ey:.0f})",
            cid=self._cam_id_str,
            sx=counting_line.start_x,
            sy=counting_line.start_y,
            ex=counting_line.end_x,
            ey=counting_line.end_y,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """True while the asyncio.Task is alive."""
        return (
            self._running
            and self._task is not None
            and not self._task.done()
        )

    async def start(self) -> None:
        """Spawn the background counting task (idempotent)."""
        if self.is_running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(),
            name=f"person-counter-{self._cam_id_str}",
        )
        logger.info(
            "PersonCounter worker started | camera_id={cid} | "
            "line=({sx:.0f},{sy:.0f})→({ex:.0f},{ey:.0f}) | "
            "orientation={orient}",
            cid=self._cam_id_str,
            sx=self._line.start_x,
            sy=self._line.start_y,
            ex=self._line.end_x,
            ey=self._line.end_y,
            orient="horizontal" if self._line.is_horizontal else "vertical",
        )

    async def stop(self) -> None:
        """Stop the worker and wait for the task to finish."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info(
            "PersonCounter worker stopped | camera_id={cid} | "
            "final: entry={e} exit={x} occupancy={o}",
            cid=self._cam_id_str,
            e=self._counter.entry_count,
            x=self._counter.exit_count,
            o=self._counter.current_occupancy,
        )

    def get_status(self) -> PersonCountStatus:
        """Return a live snapshot of counts and worker state."""
        return PersonCountStatus(
            camera_id=self._cam_id_str,
            entry_count=self._counter.entry_count,
            exit_count=self._counter.exit_count,
            current_occupancy=self._counter.current_occupancy,
            worker_running=self.is_running,
            fps=round(self._current_fps, 1),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        """
        Outer loop — runs until stop() is called.
        All exceptions are caught so the worker never crashes.
        """
        while self._running:
            t_iter_start = time.monotonic()
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise  # Let stop() handle cancellation
            except Exception as exc:
                logger.error(
                    "PersonCounter unexpected error | camera_id={cid} | {err}",
                    cid=self._cam_id_str,
                    err=str(exc),
                    exc_info=True,
                )

            # Sleep for remainder of target interval (frame-rate control)
            elapsed = time.monotonic() - t_iter_start
            sleep_time = max(0.0, self._target_interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def _run_once(self) -> None:
        """One complete iteration of the counting pipeline."""

        # ── 1. Fetch latest frame ─────────────────────────────────────────────
        frame_entry = await camera_manager.get_latest_frame(self._camera_id)
        if frame_entry is None or frame_entry.latest_frame is None:
            await asyncio.sleep(0.1)
            return

        # ── 2. Skip duplicate frames ──────────────────────────────────────────
        if frame_entry.frame_number == self._last_frame_number:
            return
        self._last_frame_number = frame_entry.frame_number
        frame = frame_entry.latest_frame

        # ── 3. Detect + Track (synchronous → thread executor) ─────────────────
        t_infer_start = time.monotonic()
        tracked: List[TrackedPerson] = await asyncio.to_thread(
            self._tracker.update, frame
        )
        infer_ms = (time.monotonic() - t_infer_start) * 1000.0

        # Store for stream overlay (bounding boxes)
        self._latest_tracked = tracked

        logger.debug(
            "PersonCounter inference | camera={cid} | persons={n} | {t:.1f}ms",
            cid=self._cam_id_str,
            n=len(tracked),
            t=infer_ms,
        )

        # ── 4. LINE-CROSSING counting (entry-only, one-time per track_id) ─────
        #
        # Logic:
        #   centroid moves from ABOVE line (side=-1) to BELOW line (side=+1)
        #   → ENTRY counted ONCE per track_id.
        #
        # _counted_ids is NEVER cleared on track loss — Phase 1 fix.
        # ByteTrack track_buffer=90 keeps the same ID for ~9 s of occlusion.
        #
        active_ids: set = set()
        for person in tracked:
            active_ids.add(person.track_id)

            # Line-crossing check (only for tracks with history)
            prev = self._prev_positions.get(person.track_id)
            if prev is not None:
                crossing = self._line.check_crossing(
                    prev[0], prev[1],
                    person.cx, person.cy,
                )
                
                # Enforce a 2.0 second cooldown per track_id to prevent double-counting
                # from line jitter, while allowing the person to turn around and exit
                last_count_time = self._counted_ids.get(person.track_id, 0.0)
                now = time.monotonic()
                
                if crossing and (now - last_count_time > 2.0):
                    if crossing == "entry":
                        self._counter.add_entry()
                        self._counted_ids[person.track_id] = now
                        logger.info(
                            "ENTRY | camera={cid} | track_id={tid} | total={e}",
                            cid=self._cam_id_str,
                            tid=person.track_id,
                            e=self._counter.entry_count,
                        )
                    elif crossing == "exit":
                        self._counter.add_exit()
                        self._counted_ids[person.track_id] = now
                        logger.info(
                            "EXIT | camera={cid} | track_id={tid} | total={x}",
                            cid=self._cam_id_str,
                            tid=person.track_id,
                            x=self._counter.exit_count,
                        )

            # Update centroid history for next frame
            self._prev_positions[person.track_id] = (person.cx, person.cy)

        # ── 5. Evict lost track IDs ───────────────────────────────────────────
        for tid in list(self._prev_positions):
            if tid not in active_ids:
                del self._prev_positions[tid]
                # _counted_ids intentionally NOT cleared on track loss



        # ── 6. FPS monitoring ─────────────────────────────────────────────────
        self._proc_frame_count += 1
        now = time.monotonic()
        window = now - self._fps_window_start
        if window >= 5.0:
            self._current_fps = self._proc_frame_count / window
            logger.info(
                "PersonCounter FPS | camera={cid} | fps={fps:.1f} | "
                "entry={e} | exit={x} | occupancy={o}",
                cid=self._cam_id_str,
                fps=self._current_fps,
                e=self._counter.entry_count,
                x=self._counter.exit_count,
                o=self._counter.current_occupancy,
            )
            self._proc_frame_count = 0
            self._fps_window_start = now

        # ── 7. Publish to Redis if counts changed (Task 7) ────────────────────
        if (
            self._counter.entry_count != self._last_pub_entry
            or self._counter.exit_count != self._last_pub_exit
        ):
            await self._publish_counts()
            self._last_pub_entry = self._counter.entry_count
            self._last_pub_exit = self._counter.exit_count

    # ── Redis publishing ──────────────────────────────────────────────────────

    async def _publish_counts(self) -> None:
        """
        Publish current counts to Redis channel:person.count.

        Only called when entry_count or exit_count changed — never on
        every frame (Task 7).

        Payload:
            {
                "camera_id": "...",
                "entry": 25,
                "exit": 18,
                "current": 7,
                "timestamp": "2026-07-25T00:00:00+00:00"
            }
        """
        snap = self._counter.snapshot()
        await event_publisher.publish(
            REDIS_CHANNEL_PERSON_COUNT,
            LiveEvent(
                event_type=_EVENT_TYPE_PERSON_COUNT,
                source="person_counter",
                payload={
                    "camera_id": self._cam_id_str,
                    "entry": snap["entry_count"],
                    "exit": snap["exit_count"],
                    "current": snap["current_occupancy"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ),
        )
        logger.debug(
            "Count published | camera={cid} | "
            "entry={e} | exit={x} | current={c}",
            cid=self._cam_id_str,
            e=snap["entry_count"],
            x=snap["exit_count"],
            c=snap["current_occupancy"],
        )

        # ── Database Persistence ──────────────────────────────────────────────
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    record = EntryExitCount(
                        camera_id=self._camera_id,
                        entry_count=snap["entry_count"],
                        exit_count=snap["exit_count"],
                        net_count=snap["current_occupancy"],
                        recorded_at=datetime.now(timezone.utc),
                    )
                    session.add(record)
        except Exception as exc:
            logger.error(
                "Failed to save EntryExitCount to DB | camera={cid} | error={err}",
                cid=self._cam_id_str,
                err=str(exc),
            )


# ─── PersonCounterManager ────────────────────────────────────────────────────


class PersonCounterManager:
    """
    Global registry of PersonCounterWorker instances.

    One worker per camera. Enforces no-duplicate-worker constraint.
    Controlled entirely through the REST API (no auto-start at startup).
    """

    def __init__(self) -> None:
        self._workers: Dict[str, PersonCounterWorker] = {}

    async def start_worker(
        self,
        camera_id: uuid.UUID,
        counting_line: CountingLine,
        target_fps: int = _DEFAULT_TARGET_FPS,
    ) -> bool:
        """
        Start a counting worker for camera_id.

        Returns:
            True  — worker started successfully.
            False — a worker is already running for this camera.
        """
        cam_id_str = str(camera_id)
        existing = self._workers.get(cam_id_str)
        if existing and existing.is_running:
            existing.update_line(counting_line)
            await self._save_config(camera_id, counting_line, target_fps)
            return True

        worker = PersonCounterWorker(camera_id, counting_line, target_fps)
        self._workers[cam_id_str] = worker
        await worker.start()

        # Persist config to Redis so it survives server restart
        await self._save_config(camera_id, counting_line, target_fps)
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
        # Remove persisted config
        await self._delete_config(camera_id)
        return True

    def get_status(self, camera_id: uuid.UUID) -> Optional[PersonCountStatus]:
        """Return status for one camera, or None if no worker exists."""
        worker = self._workers.get(str(camera_id))
        return worker.get_status() if worker else None

    def get_all_statuses(self) -> List[PersonCountStatus]:
        """Return status snapshots for all cameras (running or stopped)."""
        return [w.get_status() for w in self._workers.values()]

    @property
    def active_worker_count(self) -> int:
        """Number of currently running workers."""
        return sum(1 for w in self._workers.values() if w.is_running)

    # ── Redis persistence ────────────────────────────────────────────────────

    async def _save_config(
        self,
        camera_id: uuid.UUID,
        line: CountingLine,
        target_fps: int,
    ) -> None:
        """Save counter config to Redis HASH so it survives restart."""
        try:
            from app.utils.redis_manager import redis_manager
            cfg = json.dumps({
                "start_x": line.start_x,
                "start_y": line.start_y,
                "end_x":   line.end_x,
                "end_y":   line.end_y,
                "target_fps": target_fps,
            })
            client = redis_manager.client
            await client.hset(_REDIS_CONFIG_KEY, str(camera_id), cfg)
        except Exception as exc:
            logger.warning("Failed to persist counter config | err={e}", e=exc)

    async def _delete_config(self, camera_id: uuid.UUID) -> None:
        """Remove persisted counter config from Redis."""
        try:
            from app.utils.redis_manager import redis_manager
            client = redis_manager.client
            await client.hdel(_REDIS_CONFIG_KEY, str(camera_id))
        except Exception as exc:
            logger.warning("Failed to delete counter config | err={e}", e=exc)

    async def restore_from_redis(self) -> int:
        """
        Called at app startup: reload all persisted counter configs from Redis
        and restart workers automatically.

        Returns number of workers restored.
        """
        restored = 0
        try:
            from app.utils.redis_manager import redis_manager
            client = redis_manager.client
            configs = await client.hgetall(_REDIS_CONFIG_KEY)
            if not configs:
                logger.info("PersonCounter: no persisted configs found in Redis")
                return 0

            for cam_id_bytes, cfg_bytes in configs.items():
                try:
                    cam_id_str = cam_id_bytes.decode() if isinstance(cam_id_bytes, bytes) else cam_id_bytes
                    cfg = json.loads(cfg_bytes.decode() if isinstance(cfg_bytes, bytes) else cfg_bytes)
                    camera_id = uuid.UUID(cam_id_str)
                    line = CountingLine(
                        start_x=cfg["start_x"],
                        start_y=cfg["start_y"],
                        end_x=cfg["end_x"],
                        end_y=cfg["end_y"],
                    )
                    target_fps = cfg.get("target_fps", _DEFAULT_TARGET_FPS)
                    worker = PersonCounterWorker(camera_id, line, target_fps)
                    self._workers[cam_id_str] = worker
                    await worker.start()
                    restored += 1
                    logger.info(
                        "PersonCounter restored | camera_id={cid}",
                        cid=cam_id_str,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to restore counter for {cid} | err={e}",
                        cid=cam_id_str, e=exc,
                    )
        except Exception as exc:
            logger.warning("PersonCounter Redis restore failed | err={e}", e=exc)

        if restored:
            logger.info("PersonCounter: restored {n} worker(s) from Redis", n=restored)
        return restored


# ─── Singleton ────────────────────────────────────────────────────────────────

person_counter_manager: PersonCounterManager = PersonCounterManager()
