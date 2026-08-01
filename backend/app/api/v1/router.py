"""API v1 route aggregator."""
from fastapi import APIRouter

from app.api.v1 import (
    health,
    camera_stream,  # Phase 2 — must be registered BEFORE cameras
    cameras,
    zones,
    alerts,
    users,
    version,
    metrics,
    events,
    system_settings,
    ai,             # Phase 3 — AI infrastructure
    person_counter, # Phase 4 — person counting
    queue,          # Phase 5 — queue management
    zone,           # Phase 6 — zone monitoring
    face,           # Phase 7 — face recognition
    dashboard,      # Dashboard notification feed
)

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, prefix="/health", tags=["Health"])
# camera_stream first: /cameras/live and /cameras/reload are static paths
# that must resolve before the dynamic /cameras/{camera_id} in cameras.router
api_v1_router.include_router(camera_stream.router, tags=["Camera Stream"])
api_v1_router.include_router(cameras.router, prefix="/cameras", tags=["Cameras"])
api_v1_router.include_router(zones.router, prefix="/zones", tags=["Zones"])
api_v1_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_v1_router.include_router(users.router, prefix="/users", tags=["Users"])
api_v1_router.include_router(version.router, prefix="/version", tags=["System"])
api_v1_router.include_router(metrics.router, prefix="/metrics", tags=["System"])
api_v1_router.include_router(events.router, prefix="/events", tags=["Events"])
api_v1_router.include_router(
    system_settings.router, prefix="/settings", tags=["Settings"]
)
api_v1_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_v1_router.include_router(person_counter.router, tags=["Person Counter"])
api_v1_router.include_router(queue.router, tags=["Queue Management"])
api_v1_router.include_router(zone.router, tags=["Zone Monitoring"])
api_v1_router.include_router(face.router, tags=["Face Recognition"])
api_v1_router.include_router(dashboard.router, tags=["Dashboard"])  # notification feed

