"""ORM model imports — ensures all tables are registered with SQLAlchemy metadata."""
from app.models.camera_group import CameraGroup  # noqa: F401
from app.models.zone import Zone  # noqa: F401
from app.models.camera import Camera  # noqa: F401
from app.models.roi import ROI  # noqa: F401
from app.models.queue import Queue, QueueSnapshot  # noqa: F401
from app.models.count import EntryExitCount, ZoneCount  # noqa: F401
from app.models.alert import Alert  # noqa: F401
from app.models.camera_health import CameraHealth  # noqa: F401
from app.models.watchlist import CriminalWatchlist, FaceDetectionLog  # noqa: F401
from app.models.user import User, Role, Permission  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.system_settings import SystemSettings  # noqa: F401
from app.models.ai_model import AIModel  # noqa: F401
from app.models.service_status import ServiceStatus  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.snapshot import Snapshot  # noqa: F401
from app.models.event import Event  # noqa: F401
