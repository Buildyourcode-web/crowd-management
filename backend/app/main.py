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

    # Connect to PostgreSQL
    await connect_db()

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

    # ── Auto-start Queue Workers for all active Queue cameras in DB ────────────
    try:
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
        logger.warning("Queue auto-start error | err={e}", e=str(q_exc))

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
