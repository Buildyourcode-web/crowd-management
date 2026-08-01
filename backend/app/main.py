"""Temple AI Crowd Management System — FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_v1_router
from app.ai.gpu import log_gpu_info
from app.ai.model_manager import model_manager
from app.camera.camera_manager import camera_manager
from app.queue_management.manager import queue_manager
from app.common.constants import REDIS_CHANNEL_SYSTEM
from app.config.settings import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.database.connection import connect_db, disconnect_db
from app.events.publisher import event_publisher
from app.events.schemas import EventType, LiveEvent
from app.events.subscriber import event_subscriber
from app.middleware.request_logging import RequestLoggingMiddleware
from app.utils.redis_manager import redis_manager
from app.websocket.router import router as ws_router


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""

    # ── Startup ──────────────────────────────────────────────────────────────
    setup_logging()
    logger.info(
        "Starting {name} v{version} | env={env}",
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.ENVIRONMENT,
    )

    # Connect to PostgreSQL and create/verify tables
    await connect_db()
    try:
        await seed_initial_cameras()
    except Exception as seed_exc:
        logger.warning("Auto camera seeding skipped | err={e}", e=str(seed_exc))

    # Connect to Redis (non-fatal — app starts in degraded mode without Redis)
    try:
        await redis_manager.connect()
        logger.info("Redis connected successfully")
    except Exception as exc:
        logger.warning(
            "Redis unavailable at startup — running in DEGRADED mode. "
            "Zone live-counts and WebSocket pub/sub will not work until Redis is reachable. "
            "Error: {err}",
            err=str(exc),
        )

    # Start RTSP camera infrastructure (non-fatal — idle if no cameras configured)
    try:
        await camera_manager.startup()
    except Exception as exc:
        logger.warning(
            "CameraManager startup failed — no streams running. Error: {err}",
            err=str(exc),
        )

    # Start Redis Event Subscriber (Task 8)
    try:
        await event_subscriber.start()
        await event_publisher.publish(
            REDIS_CHANNEL_SYSTEM,
            LiveEvent(
                event_type=EventType.SYSTEM_STARTUP,
                source="main",
                payload={
                    "app": settings.APP_NAME,
                    "version": settings.APP_VERSION,
                    "environment": settings.ENVIRONMENT,
                },
            ),
        )
    except Exception as exc:
        logger.warning(
            "EventSubscriber startup failed. Error: {err}", err=str(exc)
        )

    logger.info("{name} startup complete", name=settings.APP_NAME)

    # ── AI Infrastructure — GPU detection + YOLO loading (Task 7) ────────────
    # Run in thread executor: YOLO loading is blocking/synchronous (~5-10 s).
    # Non-fatal — server stays up even if the model file is missing.
    import asyncio
    try:
        log_gpu_info()                              # step 1: log GPU info
        success = await asyncio.to_thread(model_manager.load_model)  # steps 2-3
        if success:
            logger.info(
                "YOLO model ready | name={n} | device={d}",
                n=model_manager.model_name,
                d=model_manager.device,
            )
        else:
            logger.warning(
                "YOLO model NOT loaded — AI inference unavailable. "
                "Check AI_MODEL_PATH in settings."
            )
    except Exception as exc:
        logger.error(
            "AI startup error — model NOT loaded. Error: {err}", err=str(exc)
        )

    # ── Restore PersonCounter workers (Redis → DB fallback) ───────────────────
    try:
        from app.person_counter.worker import person_counter_manager
        from app.person_counter.roi import CountingLine
        from app.database.connection import AsyncSessionLocal
        from sqlalchemy import text

        n = await person_counter_manager.restore_from_redis()
        if n:
            logger.info("PersonCounter: {n} worker(s) restored from Redis", n=n)

        # Auto-start worker for any active AI-enabled camera not yet running
        async with AsyncSessionLocal() as session:
            rows = await session.execute(text(
                "SELECT id, camera_name, resolution FROM cameras "
                "WHERE is_active = true AND ai_enabled = true AND stream_enabled = true"
            ))
            cameras = rows.fetchall()

        started = 0
        for cam in cameras:
            cam_id_str = str(cam.id)
            if cam_id_str not in person_counter_manager._workers or not person_counter_manager._workers[cam_id_str].is_running:
                try:
                    cam_id = cam.id
                    res = (cam.resolution or "1920x1080").split("x")
                    w = int(res[0]) if len(res) > 0 and res[0].isdigit() else 1920
                    h = int(res[1]) if len(res) > 1 and res[1].isdigit() else 1080
                    line = CountingLine(
                        start_x=0.0,
                        start_y=float(h) * 0.5,
                        end_x=float(w),
                        end_y=float(h) * 0.5,
                    )
                    ok = await person_counter_manager.start_worker(cam_id, line)
                    if ok:
                        started += 1
                        logger.info(
                            "PersonCounter auto-started | camera={name} | id={cid}",
                            name=cam.camera_name,
                            cid=cam_id_str,
                        )
                except Exception as cam_exc:
                    logger.warning(
                        "PersonCounter auto-start failed | cid={cid} | err={e}",
                        cid=cam.id, e=cam_exc,
                    )
        if started:
            logger.info("PersonCounter: {n} worker(s) auto-started from DB", n=started)
    except Exception as exc:
        logger.warning("PersonCounter startup skipped | err={err}", err=str(exc))

    # ── Auto-start Queue Workers (Redis restore → DB query → Fallback defaults) ────────────
    try:
        # Step 1: Restore from Redis if available
        n_restored = await queue_manager.restore_from_redis()
        if n_restored:
            logger.info("QueueManager: {n} worker(s) restored from Redis", n=n_restored)

        # Step 2: Query DB for active queue cameras
        from app.models.roi import ROI
        from app.models.camera import Camera
        from app.common.enums import ROIType, CameraType
        from app.queue_management.roi import QueueROI
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            res_cams = await session.execute(select(Camera).where(Camera.is_active == True))
            cams = res_cams.scalars().all()

            for cam_obj in cams:
                if cam_obj.camera_type == CameraType.QUEUE or str(cam_obj.id).startswith("4e09b542") or str(cam_obj.id).startswith("67676767"):
                    res_r = await session.execute(select(ROI).where(ROI.camera_id == cam_obj.id))
                    rois = res_r.scalars().all()
                    q_roi_obj = None
                    for r in rois:
                        if r.roi_type == ROIType.POLYGON_ZONE or "Queue" in (r.name or ""):
                            q_roi_obj = r
                            break

                    p = (q_roi_obj.polygon if q_roi_obj and isinstance(q_roi_obj.polygon, dict) else {}) or {}
                    x1 = float(p.get("x1", 1000 if "4e09b542" in str(cam_obj.id) else 100))
                    y1 = float(p.get("y1", 120 if "4e09b542" in str(cam_obj.id) else 100))
                    x2 = float(p.get("x2", 1820 if "4e09b542" in str(cam_obj.id) else 1800))
                    y2 = float(p.get("y2", 1080 if "4e09b542" in str(cam_obj.id) else 1000))

                    q_roi = QueueROI(x1=x1, y1=y1, x2=x2, y2=y2)
                    await queue_manager.start_worker(
                        camera_id=cam_obj.id,
                        roi=q_roi,
                        direction="DOWN"
                    )
                    logger.info("Auto-started QueueWorker for camera | id={cid} | name={n}", cid=cam_obj.id, n=cam_obj.camera_name)
    except Exception as q_exc:
        logger.warning("Queue auto-start from DB skipped/failed | err={e} — using fallback defaults", e=str(q_exc))
        # Fallback: start default workers for Camera 1 and Camera 2 if DB unavailable
        import uuid
        from app.queue_management.roi import QueueROI
        cam1_id = uuid.UUID('4e09b542-98b1-4974-9e6c-8f3a8c3d7f0a')
        cam2_id = uuid.UUID('67676767-6767-4e67-a676-676767676767')
        await queue_manager.start_worker(cam1_id, QueueROI(1000, 120, 1820, 1080), direction="DOWN")
        await queue_manager.start_worker(cam2_id, QueueROI(450, 200, 1650, 980), direction="DOWN")
        logger.info("Fallback QueueWorkers started for Cam 1 & Cam 2")

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down {name}...", name=settings.APP_NAME)
    # Publish system.shutdown before stopping subscriber
    await event_publisher.publish(
        REDIS_CHANNEL_SYSTEM,
        LiveEvent(
            event_type=EventType.SYSTEM_SHUTDOWN,
            source="main",
            payload={"app": settings.APP_NAME},
        ),
    )
    await event_subscriber.stop()        # Stop Redis listener
    model_manager.unload_model()         # Release YOLO model from GPU memory
    await camera_manager.shutdown()      # Stop all RTSP workers
    await redis_manager.disconnect()
    await disconnect_db()
    logger.info("{name} shutdown complete", name=settings.APP_NAME)


# ─── Application Factory ──────────────────────────────────────────────────────

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "Health", "description": "System health and status checks"},
            {"name": "Cameras", "description": "Camera configuration management"},
            {"name": "Zones", "description": "Temple zone management"},
            {"name": "Alerts", "description": "Alert creation and management"},
            {"name": "Users", "description": "User management"},
            {"name": "Events", "description": "Unified system event log"},
            {"name": "Settings", "description": "System configuration settings"},
            {"name": "System", "description": "Version and metrics"},
        ],
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.ALLOW_CREDENTIALS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    # ── Request Logging ───────────────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception Handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── API Routes ────────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # ── Legacy / Laravel Dashboard Data Endpoint ──────────────────────────────
    @app.get("/api/crowd-data")
    async def get_crowd_data():
        from app.person_counter.worker import person_counter_manager
        statuses = person_counter_manager.get_all_statuses()
        total_in = sum((s.entry_count for s in statuses))
        total_out = sum((s.exit_count for s in statuses))
        
        return {
            "success": True,
            "system": {
                "status": "live",
                "ai_connected": True,
                "camera_connected": len(statuses) > 0,
            },
            "summary": {
                "total_entries": total_in,
                "total_exits": total_out,
                "total_visits": total_in
            },
            "zones": [
                {
                    "id": "main-zone",
                    "name": "Main Entrance Zone",
                    "current_count": total_in - total_out,
                    "capacity": 1000
                }
            ],
            "gates": [],
            "queues": []
        }

    # ── WebSocket Routes ──────────────────────────────────────────────────────
    app.include_router(ws_router)

    return app


# Application instance
app: FastAPI = create_application()


async def seed_initial_cameras() -> None:
    """Ensure Camera 1, Camera 2, and Camera 3 and their ROIs exist in DB automatically."""
    import uuid
    from app.database.connection import AsyncSessionLocal
    from app.models.camera import Camera
    from app.models.roi import ROI
    from app.common.enums import CameraType, CameraStatus, ROIType
    from sqlalchemy import select

    cam1_id = uuid.UUID('4e09b542-98b1-4974-9e6c-8f3a8c3d7f0a')
    cam2_id = uuid.UUID('67676767-6767-4e67-a676-676767676767')
    cam3_id = uuid.UUID('33333333-3333-4333-a333-333333333333')
    cam4_id = uuid.UUID('44444444-4444-4444-a444-444444444444')
    cam5_id = uuid.UUID('55555555-5555-5555-a555-555555555555')
    cam6_id = uuid.UUID('66666666-6666-6666-a666-666666666666')

    async with AsyncSessionLocal() as session:
        # Check Camera 1
        res1 = await session.execute(select(Camera).where(Camera.id == cam1_id))
        if not res1.scalar_one_or_none():
            c1 = Camera(
                id=cam1_id,
                camera_name="Queue Monitor 1 (192.168.1.78)",
                camera_type=CameraType.QUEUE,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                rtsp_url="rtsp://admin:cctv%40321@192.168.1.78:554/Streaming/Channels/101",
                location="Main Queue Pathway 1"
            )
            session.add(c1)
            roi1 = ROI(
                id=uuid.uuid4(),
                camera_id=cam1_id,
                name="Queue Walkway ROI 1",
                roi_type=ROIType.POLYGON_ZONE,
                polygon={"x1": 1000, "y1": 120, "x2": 1820, "y2": 1080},
                is_active=True
            )
            session.add(roi1)

        # Check Camera 2
        res2 = await session.execute(select(Camera).where(Camera.id == cam2_id))
        if not res2.scalar_one_or_none():
            c2 = Camera(
                id=cam2_id,
                camera_name="Queue Monitor 2 (192.168.1.65)",
                camera_type=CameraType.QUEUE,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                rtsp_url="rtsp://admin:cctv%40321@192.168.1.65:554/Streaming/Channels/101",
                location="Main Queue Pathway 2"
            )
            session.add(c2)
            roi2 = ROI(
                id=uuid.uuid4(),
                camera_id=cam2_id,
                name="Queue Walkway ROI 2",
                roi_type=ROIType.POLYGON_ZONE,
                polygon={"x1": 450, "y1": 200, "x2": 1650, "y2": 980},
                is_active=True
            )
            session.add(roi2)

        # Check Camera 3
        res3 = await session.execute(select(Camera).where(Camera.id == cam3_id))
        if not res3.scalar_one_or_none():
            c3 = Camera(
                id=cam3_id,
                camera_name="Entry Counter Camera 3 (192.168.1.100)",
                camera_type=CameraType.ENTRY,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                ai_enabled=True,
                rtsp_url="rtsp://admin:Admin%40123@192.168.1.100:554/cam/realmonitor?channel=13&subtype=0",
                resolution="2560x1440",
                location="Main Gate Entrance 3"
            )
            session.add(c3)
            roi3 = ROI(
                id=uuid.uuid4(),
                camera_id=cam3_id,
                name="Main Entrance Counting Line 3",
                roi_type=ROIType.COUNTING_LINE,
                polygon={
                    "start_x": 0.0,
                    "start_y": 720.0,
                    "end_x": 2560.0,
                    "end_y": 720.0,
                    "orientation": "horizontal"
                },
                is_active=True
            )
            session.add(roi3)

        # Check Camera 4 (Exit Counter)
        res4 = await session.execute(select(Camera).where(Camera.id == cam4_id))
        if not res4.scalar_one_or_none():
            c4 = Camera(
                id=cam4_id,
                camera_name="Exit Counter Camera 4 (192.168.1.100 ch15)",
                camera_type=CameraType.EXIT,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                ai_enabled=True,
                rtsp_url="rtsp://admin:Admin%40123@192.168.1.100:554/cam/realmonitor?channel=15&subtype=1",
                resolution="1920x1080",
                location="Main Gate Exit 4"
            )
            session.add(c4)
            roi4 = ROI(
                id=uuid.uuid4(),
                camera_id=cam4_id,
                name="Main Exit Counting Line 4",
                roi_type=ROIType.COUNTING_LINE,
                polygon={
                    "start_x": 0.0,
                    "start_y": 540.0,
                    "end_x": 1920.0,
                    "end_y": 540.0,
                    "orientation": "horizontal"
                },
                is_active=True
            )
            session.add(roi4)

        # Check Camera 5 (Exit Counter)
        res5 = await session.execute(select(Camera).where(Camera.id == cam5_id))
        if not res5.scalar_one_or_none():
            c5 = Camera(
                id=cam5_id,
                camera_name="Exit Counter Camera 5 (192.168.1.243)",
                camera_type=CameraType.EXIT,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                ai_enabled=True,
                rtsp_url="rtsp://admin:Admin%40123@192.168.1.243:554/video/live?channel=1&subtype=0",
                resolution="1920x1080",
                location="Main Gate Exit 5"
            )
            session.add(c5)
            roi5 = ROI(
                id=uuid.uuid4(),
                camera_id=cam5_id,
                name="Main Exit Counting Line 5",
                roi_type=ROIType.COUNTING_LINE,
                polygon={
                    "start_x": 0.0,
                    "start_y": 540.0,
                    "end_x": 1920.0,
                    "end_y": 540.0,
                    "orientation": "horizontal"
                },
                is_active=True
            )
            session.add(roi5)

        # Check Camera 6 (Person Counter)
        res6 = await session.execute(select(Camera).where(Camera.id == cam6_id))
        if not res6.scalar_one_or_none():
            c6 = Camera(
                id=cam6_id,
                camera_name="Person Counter Camera 6 (192.168.1.100 ch12)",
                camera_type=CameraType.ENTRY,
                status=CameraStatus.ONLINE,
                is_active=True,
                stream_enabled=True,
                ai_enabled=True,
                rtsp_url="rtsp://admin:Admin%40123@192.168.1.100:554/cam/realmonitor?channel=12&subtype=0",
                resolution="1920x1080",
                location="Main Gate Entrance 6"
            )
            session.add(c6)
            roi6 = ROI(
                id=uuid.uuid4(),
                camera_id=cam6_id,
                name="Main Entrance Counting Line 6",
                roi_type=ROIType.COUNTING_LINE,
                polygon={
                    "start_x": 0.0,
                    "start_y": 540.0,
                    "end_x": 1920.0,
                    "end_y": 540.0,
                    "orientation": "horizontal"
                },
                is_active=True
            )
            session.add(roi6)

        await session.commit()
