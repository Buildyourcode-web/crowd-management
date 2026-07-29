"""Application-wide constants for Temple AI Crowd Management System."""

# ─── Application ──────────────────────────────────────────────────────────────
APP_NAME: str = "Temple AI Crowd Management System"
API_PREFIX: str = "/api/v1"

# ─── Pagination ───────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
MIN_PAGE: int = 1

# ─── Camera ───────────────────────────────────────────────────────────────────
CAMERA_INITIAL_COUNT: int = 13          # Bonalu initial deployment
CAMERA_MAX_FUTURE: int = 200            # Planned maximum
CAMERA_HEALTH_CHECK_INTERVAL: int = 30  # seconds
CAMERA_RECONNECT_ATTEMPTS: int = 5
CAMERA_RECONNECT_DELAY: int = 10        # seconds between retries
CAMERA_DEFAULT_FPS: int = 15
CAMERA_DEFAULT_RESOLUTION: str = "1920x1080"

# ─── Zone ─────────────────────────────────────────────────────────────────────
ZONE_WARNING_THRESHOLD_PCT: int = 80   # % of capacity → warning
ZONE_CRITICAL_THRESHOLD_PCT: int = 95  # % of capacity → critical
ZONE_COUNT_TTL_SECONDS: int = 300      # Redis key TTL for zone counts

# ─── Queue ────────────────────────────────────────────────────────────────────
QUEUE_SNAPSHOT_INTERVAL: int = 60      # seconds
QUEUE_NORMAL_THRESHOLD: int = 30       # people
QUEUE_MODERATE_THRESHOLD: int = 60     # people
QUEUE_HEAVY_THRESHOLD: int = 100       # people

# ─── Alert ────────────────────────────────────────────────────────────────────
ALERT_COOLDOWN_SECONDS: int = 300      # prevent duplicate alerts within 5 min
ALERT_AUTO_RESOLVE_HOURS: int = 24
ALERT_RETENTION_DAYS: int = 90

# ─── AI / Detection ───────────────────────────────────────────────────────────
DEFAULT_CONFIDENCE: float = 0.5
DEFAULT_IOU: float = 0.45
DEFAULT_DETECTION_FPS: int = 5
DEFAULT_SNAPSHOT_INTERVAL: int = 30    # seconds

# ─── Redis Keys (use .format() or f-string to interpolate) ───────────────────
REDIS_KEY_ZONE_COUNT: str = "zone:count:{zone_id}"
REDIS_KEY_CAMERA_STATUS: str = "camera:status:{camera_id}"
REDIS_KEY_SERVICE_STATUS: str = "service:status:{service_name}"
REDIS_KEY_SYSTEM_METRICS: str = "system:metrics"
REDIS_CHANNEL_ALERTS: str = "channel:alerts"
REDIS_CHANNEL_EVENTS: str = "channel:events"
REDIS_CHANNEL_METRICS: str = "channel:metrics"

# ─── Phase 2B — Live Communication Layer channels ─────────────────────────────
REDIS_CHANNEL_CAMERA_STATUS: str = "channel:camera.status"
REDIS_CHANNEL_CAMERA_HEALTH: str = "channel:camera.health"
REDIS_CHANNEL_SYSTEM: str = "channel:system.events"

# ─── Phase 4 — Person Counter ────────────────────────────────────────────────
REDIS_CHANNEL_PERSON_COUNT: str = "channel:person.count"

# ─── Phase 5 — Queue Management ──────────────────────────────────────────────
REDIS_CHANNEL_QUEUE_STATUS: str = "channel:queue.status"

# ─── Phase 6 — Zone Monitoring ───────────────────────────────────────────────
REDIS_CHANNEL_ZONE_STATUS: str = "channel:zone.status"

# ─── Phase 7 — Face Recognition ──────────────────────────────────────────────
REDIS_CHANNEL_FACE_MATCH: str = "channel:face.match"

# ─── WebSocket Rooms ──────────────────────────────────────────────────────────
WS_ROOM_ALERTS: str = "alerts"
WS_ROOM_METRICS: str = "metrics"
WS_ROOM_CAMERA: str = "camera:{camera_id}"
WS_ROOM_ZONE: str = "zone:{zone_id}"
WS_ROOM_DASHBOARD: str = "dashboard"

# ─── HTTP Headers ─────────────────────────────────────────────────────────────
HEADER_REQUEST_ID: str = "X-Request-ID"
HEADER_API_VERSION: str = "X-API-Version"

# ─── Notification ─────────────────────────────────────────────────────────────
NOTIFICATION_MAX_RETRIES: int = 3
NOTIFICATION_RETRY_DELAY: int = 60  # seconds

# ─── Audit ────────────────────────────────────────────────────────────────────
AUDIT_LOG_RETENTION_DAYS: int = 365

# ─── Logging Format ───────────────────────────────────────────────────────────
LOG_FORMAT_CONSOLE: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
LOG_FORMAT_FILE: str = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{extra[request_id]} | "
    "{message}"
)
