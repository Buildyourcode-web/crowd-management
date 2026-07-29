"""
FaceWorker — per-camera face recognition asyncio.Task (Tasks 7, 9, 11, 12, 13, 14).

═══════════════════════════════════════════════════════════════════════
Worker lifecycle (Task 11)
═══════════════════════════════════════════════════════════════════════

    start()   → ensures InsightFace is loaded, spawns asyncio.Task
    stop()    → cancels task, waits up to 5 s
    restart() → stop() then start()

Automatic recovery: every exception in _run_loop is caught, logged,
and the loop continues (never crashes FastAPI — Task 14).

═══════════════════════════════════════════════════════════════════════
Per-frame pipeline (Task 7)
═══════════════════════════════════════════════════════════════════════

    1. camera_manager.get_latest_frame()        [async]
    2. Skip if frame_number unchanged           [frame dedup]
    3. asyncio.to_thread(face_detector.detect)  [blocking → thread]
    4. For each face: face_matcher.match()      [in-memory only]
    5. If matched + cooldown expired → publish  [Task 9]
    6. FPS / counters logged every 5 s          [Task 12]

═══════════════════════════════════════════════════════════════════════
Cooldown (Task 9)
═══════════════════════════════════════════════════════════════════════

Per (camera_id, person_id) pair, a 30-second cooldown prevents
the same person being published repeatedly while in frame.

    _cooldowns: Dict[str, float]   — person_id → monotonic timestamp
    _is_cooldown_expired(person_id) → True if ≥ 30 s since last publish

Redis payload on match:
    {
        "camera_id":  "...",
        "person_id":  "P102",
        "name":       "John Doe",
        "similarity": 0.82,
        "timestamp":  "2026-07-25T00:00:00+00:00"
    }

═══════════════════════════════════════════════════════════════════════
Performance (Task 13)
═══════════════════════════════════════════════════════════════════════

• Target: 3 FPS (face recognition is slower than queue/zone, 3 FPS
  is appropriate for entry monitoring)
• Frame deduplication via frame_number
• InsightFace runs in thread executor (event loop never blocked)
• Embeddings fetched from in-memory cache — zero DB queries per frame
• Model loaded once per process (FaceModelManager singleton)
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from loguru import logger

from app.camera.camera_manager import camera_manager
from app.common.constants import REDIS_CHANNEL_FACE_MATCH
from app.events.publisher import event_publisher
from app.events.schemas import LiveEvent
from app.face_recognition.database import face_database
from app.face_recognition.detector import face_detector, face_model_manager
from app.face_recognition.matcher import face_matcher, DEFAULT_THRESHOLD
from app.face_recognition.schemas import FaceWorkerStatus

_EVENT_TYPE_FACE: str = "face.match"
_DEFAULT_TARGET_FPS: int = 3    # Face recognition at 3 FPS
_COOLDOWN_SECONDS: int = 30     # Per-(camera, person) cooldown


class FaceWorker:
    """
    Face recognition worker for one camera.

    Owns:
        - Reference to shared face_detector (singleton)
        - Reference to shared face_matcher (singleton)
        - Per-worker cooldown state

    Does NOT own the InsightFace model (shared via face_model_manager).
    Does NOT query PostgreSQL per frame (reads from face_database cache).
    """

    def __init__(
        self,
        camera_id: uuid.UUID,
        threshold: float = DEFAULT_THRESHOLD,
        target_fps: int = _DEFAULT_TARGET_FPS,
        cooldown_seconds: int = _COOLDOWN_SECONDS,
    ) -> None:
        self._camera_id = camera_id
        self._cam_id_str = str(camera_id)
        self._threshold = threshold
        self._target_interval: float = 1.0 / max(1, target_fps)
        self._cooldown_seconds = cooldown_seconds

        # Runtime state
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._last_frame_number: int = -1

        # Per-person cooldown: person_id → last publish monotonic time
        self._cooldowns: Dict[str, float] = {}

        # Counters for logging / status
        self._faces_detected: int = 0
        self._matches: int = 0
        self._unknowns: int = 0
        self._proc_count: int = 0
        self._fps_window_start: float = time.monotonic()
        self._current_fps: float = 0.0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return (
            self._running
            and self._task is not None
            and not self._task.done()
        )

    async def start(self) -> None:
        """
        Ensure InsightFace is loaded, then spawn the worker task.
        Model loading (~10 s first time) runs in thread executor.
        """
        if self.is_running:
            return

        # Load InsightFace once (idempotent — instant no-op on subsequent calls)
        logger.info(
            "FaceWorker | Ensuring InsightFace loaded | camera_id={cid}",
            cid=self._cam_id_str,
        )
        await asyncio.to_thread(face_model_manager.ensure_loaded, 0)

        # Ensure DB + cache initialized
        await face_database.ensure_initialized()

        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(),
            name=f"face-worker-{self._cam_id_str}",
        )
        logger.info(
            "FaceWorker started | camera_id={cid} | "
            "threshold={t} | fps={fps} | cooldown={cd}s",
            cid=self._cam_id_str,
            t=self._threshold,
            fps=round(1.0 / self._target_interval),
            cd=self._cooldown_seconds,
        )

    async def stop(self) -> None:
        """Stop the worker and wait for clean shutdown."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info(
            "FaceWorker stopped | camera_id={cid} | "
            "detected={d} | matched={m} | unknown={u}",
            cid=self._cam_id_str,
            d=self._faces_detected,
            m=self._matches,
            u=self._unknowns,
        )

    async def restart(self) -> None:
        """Stop then start — resets cooldowns and counters."""
        await self.stop()
        self._cooldowns.clear()
        await self.start()
        logger.info(
            "FaceWorker restarted | camera_id={cid}", cid=self._cam_id_str
        )

    def get_status(self) -> FaceWorkerStatus:
        return FaceWorkerStatus(
            camera_id=self._cam_id_str,
            worker_running=self.is_running,
            faces_detected_total=self._faces_detected,
            matches_total=self._matches,
            unknowns_total=self._unknowns,
            fps=round(self._current_fps, 1),
            threshold=self._threshold,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        """Outer loop — runs until stop(). Catches and logs all exceptions."""
        while self._running:
            t_iter_start = time.monotonic()
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "FaceWorker error | camera_id={cid} | {err}",
                    cid=self._cam_id_str,
                    err=str(exc),
                    exc_info=True,
                )
            elapsed = time.monotonic() - t_iter_start
            await asyncio.sleep(max(0.0, self._target_interval - elapsed))

    async def _run_once(self) -> None:
        """One complete face recognition iteration."""

        # ── 1. Get latest frame ───────────────────────────────────────────────
        frame_entry = await camera_manager.get_latest_frame(self._camera_id)
        if frame_entry is None or frame_entry.latest_frame is None:
            await asyncio.sleep(0.1)
            return

        # ── 2. Frame deduplication ────────────────────────────────────────────
        if frame_entry.frame_number == self._last_frame_number:
            return
        self._last_frame_number = frame_entry.frame_number
        frame = frame_entry.latest_frame

        # ── 3. Detect faces + extract embeddings (thread executor) ────────────
        t_detect = time.monotonic()
        faces = await asyncio.to_thread(face_detector.detect, frame)
        detect_ms = (time.monotonic() - t_detect) * 1000.0

        self._faces_detected += len(faces)

        logger.debug(
            "FaceWorker | camera={cid} | faces_detected={n} | detect={t:.1f}ms",
            cid=self._cam_id_str,
            n=len(faces),
            t=detect_ms,
        )

        if not faces:
            self._update_fps()
            return

        # ── 4. Match each face against in-memory cache ────────────────────────
        registered = face_database.get_all_for_matching()

        for face in faces:
            result = face_matcher.match(face.embedding, registered, self._threshold)

            if result.matched:
                self._matches += 1
                logger.info(
                    "FaceWorker | MATCH | camera={cid} | person={pid} | "
                    "name={name} | score={s:.4f}",
                    cid=self._cam_id_str,
                    pid=result.person_id,
                    name=result.name,
                    s=result.similarity,
                )
                # ── 5. Publish if cooldown expired ────────────────────────────
                if self._is_cooldown_expired(result.person_id):
                    await self._publish(result)
                    self._cooldowns[result.person_id] = time.monotonic()
            else:
                self._unknowns += 1
                logger.debug(
                    "FaceWorker | UNKNOWN | camera={cid} | best_score={s:.4f}",
                    cid=self._cam_id_str,
                    s=result.similarity,
                )

        # ── 6. FPS logging ────────────────────────────────────────────────────
        self._update_fps()

    def _update_fps(self) -> None:
        """Update FPS measurement; log every 5 seconds."""
        self._proc_count += 1
        now = time.monotonic()
        window = now - self._fps_window_start
        if window >= 5.0:
            self._current_fps = self._proc_count / window
            logger.info(
                "FaceWorker FPS | camera={cid} | fps={fps:.1f} | "
                "detected={d} | matched={m} | unknown={u}",
                cid=self._cam_id_str,
                fps=self._current_fps,
                d=self._faces_detected,
                m=self._matches,
                u=self._unknowns,
            )
            self._proc_count = 0
            self._fps_window_start = now

    def _is_cooldown_expired(self, person_id: str) -> bool:
        """Return True if the per-person cooldown has expired."""
        last = self._cooldowns.get(person_id, 0.0)
        return (time.monotonic() - last) >= self._cooldown_seconds

    # ── Redis publishing ──────────────────────────────────────────────────────

    async def _publish(self, result) -> None:
        """
        Publish a face match event to Redis channel:face.match.

        Only called when a person is matched AND the per-person cooldown
        has expired. Never publishes every frame, never publishes unknowns.

        Payload:
            {
                "camera_id":  "...",
                "person_id":  "P102",
                "name":       "John Doe",
                "similarity": 0.82,
                "timestamp":  "..."
            }
        """
        await event_publisher.publish(
            REDIS_CHANNEL_FACE_MATCH,
            LiveEvent(
                event_type=_EVENT_TYPE_FACE,
                source="face_worker",
                payload={
                    "camera_id":  self._cam_id_str,
                    "person_id":  result.person_id,
                    "name":       result.name,
                    "similarity": result.similarity,
                    "timestamp":  datetime.now(timezone.utc).isoformat(),
                },
            ),
        )
        logger.info(
            "FaceWorker | Published | camera={cid} | person={pid} | score={s:.4f}",
            cid=self._cam_id_str,
            pid=result.person_id,
            s=result.similarity,
        )
