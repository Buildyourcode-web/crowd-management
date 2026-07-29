"""Application-wide enumerations for Temple AI Crowd Management System."""
from enum import Enum


class CameraType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE = "ZONE"
    QUEUE = "QUEUE"
    FACE = "FACE"


class CameraStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    ERROR = "ERROR"


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertType(str, Enum):
    CROWD_OVERFLOW = "CROWD_OVERFLOW"
    QUEUE_CRITICAL = "QUEUE_CRITICAL"
    CAMERA_OFFLINE = "CAMERA_OFFLINE"
    FACE_MATCH = "FACE_MATCH"
    ZONE_CAPACITY = "ZONE_CAPACITY"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class QueueStatusEnum(str, Enum):
    NORMAL = "NORMAL"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"
    CRITICAL = "CRITICAL"


class ROIDirection(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    BOTH = "BOTH"


class ROIType(str, Enum):
    COUNTING_LINE = "COUNTING_LINE"
    POLYGON_ZONE = "POLYGON_ZONE"
    ENTRY_GATE = "ENTRY_GATE"
    EXIT_GATE = "EXIT_GATE"
    RESTRICTED = "RESTRICTED"


class EventType(str, Enum):
    QUEUE_ALERT = "QUEUE_ALERT"
    ZONE_ALERT = "ZONE_ALERT"
    CAMERA_OFFLINE = "CAMERA_OFFLINE"
    CAMERA_ONLINE = "CAMERA_ONLINE"
    FACE_MATCH = "FACE_MATCH"
    ENTRY_CLOSED = "ENTRY_CLOSED"
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"
    AI_MODEL_LOADED = "AI_MODEL_LOADED"
    AI_MODEL_ERROR = "AI_MODEL_ERROR"
    CROWD_SURGE = "CROWD_SURGE"
    CAMERA_ERROR = "CAMERA_ERROR"


class EventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServiceName(str, Enum):
    PERSON_DETECTION = "PERSON_DETECTION"
    QUEUE_ANALYSIS = "QUEUE_ANALYSIS"
    ZONE_MONITORING = "ZONE_MONITORING"
    FACE_RECOGNITION = "FACE_RECOGNITION"
    CAMERA_STREAM = "CAMERA_STREAM"
    ALERT_ENGINE = "ALERT_ENGINE"


class ServiceStatusEnum(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    STARTING = "STARTING"
    STOPPING = "STOPPING"


class NotificationChannel(str, Enum):
    SMS = "SMS"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    DASHBOARD = "DASHBOARD"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"


class SnapshotType(str, Enum):
    FACE_DETECTION = "FACE_DETECTION"
    ZONE_ALERT = "ZONE_ALERT"
    CROWD_ALERT = "CROWD_ALERT"
    CAMERA_HEALTH = "CAMERA_HEALTH"


class AIModelType(str, Enum):
    YOLO = "YOLO"
    FACE_RECOGNITION = "FACE_RECOGNITION"
    POSE_ESTIMATION = "POSE_ESTIMATION"
    CROWD_ANALYSIS = "CROWD_ANALYSIS"
