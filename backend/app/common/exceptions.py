"""Custom exception hierarchy for Temple AI Crowd Management System."""
from typing import Any, Optional


class AppException(Exception):
    """Root exception. All custom exceptions inherit from this."""

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        detail: Optional[Any] = None,
    ) -> None:
        self.message = message
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "detail": self.detail,
        }


# ─── Database ─────────────────────────────────────────────────────────────────

class DatabaseException(AppException):
    http_status = 503
    error_code = "DATABASE_ERROR"


class DatabaseConnectionException(DatabaseException):
    error_code = "DATABASE_CONNECTION_FAILED"

    def __init__(self, detail: Optional[Any] = None) -> None:
        super().__init__("Failed to connect to the database", detail)


class DatabaseQueryException(DatabaseException):
    error_code = "DATABASE_QUERY_FAILED"


# ─── Redis ────────────────────────────────────────────────────────────────────

class RedisException(AppException):
    http_status = 503
    error_code = "REDIS_ERROR"


class RedisConnectionException(RedisException):
    error_code = "REDIS_CONNECTION_FAILED"

    def __init__(self, detail: Optional[Any] = None) -> None:
        super().__init__("Failed to connect to Redis", detail)


# ─── Resource ─────────────────────────────────────────────────────────────────

class NotFoundException(AppException):
    http_status = 404
    error_code = "NOT_FOUND"

    def __init__(self, resource: str, identifier: Any = None) -> None:
        detail = f"id={identifier}" if identifier else None
        super().__init__(f"{resource} not found", detail)


class ConflictException(AppException):
    http_status = 409
    error_code = "CONFLICT"

    def __init__(self, resource: str, field: str, value: Any) -> None:
        super().__init__(
            f"{resource} with {field}='{value}' already exists",
            {"field": field, "value": value},
        )


class ValidationException(AppException):
    http_status = 422
    error_code = "VALIDATION_ERROR"


# ─── Camera ───────────────────────────────────────────────────────────────────

class CameraException(AppException):
    http_status = 400
    error_code = "CAMERA_ERROR"


class CameraNotFoundException(NotFoundException):
    def __init__(self, camera_id: Any = None) -> None:
        super().__init__("Camera", camera_id)


class CameraAlreadyExistsException(ConflictException):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__("Camera", field, value)


class CameraInactiveException(CameraException):
    error_code = "CAMERA_INACTIVE"

    def __init__(self, camera_id: Any = None) -> None:
        super().__init__(f"Camera {camera_id} is not active")


# ─── Zone ─────────────────────────────────────────────────────────────────────

class ZoneNotFoundException(NotFoundException):
    def __init__(self, zone_id: Any = None) -> None:
        super().__init__("Zone", zone_id)


class ZoneCapacityException(AppException):
    http_status = 400
    error_code = "ZONE_CAPACITY_EXCEEDED"


# ─── Alert ────────────────────────────────────────────────────────────────────

class AlertNotFoundException(NotFoundException):
    def __init__(self, alert_id: Any = None) -> None:
        super().__init__("Alert", alert_id)


# ─── User ─────────────────────────────────────────────────────────────────────

class UserNotFoundException(NotFoundException):
    def __init__(self, user_id: Any = None) -> None:
        super().__init__("User", user_id)


class UserAlreadyExistsException(ConflictException):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__("User", field, value)


class AuthenticationException(AppException):
    http_status = 401
    error_code = "AUTHENTICATION_FAILED"

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class AuthorizationException(AppException):
    http_status = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "You do not have permission") -> None:
        super().__init__(message)


# ─── Camera Group ─────────────────────────────────────────────────────────────

class CameraGroupNotFoundException(NotFoundException):
    def __init__(self, group_id: Any = None) -> None:
        super().__init__("CameraGroup", group_id)


class CameraGroupAlreadyExistsException(ConflictException):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__("CameraGroup", field, value)


# ─── System ───────────────────────────────────────────────────────────────────

class ServiceUnavailableException(AppException):
    http_status = 503
    error_code = "SERVICE_UNAVAILABLE"


class RateLimitException(AppException):
    http_status = 429
    error_code = "RATE_LIMIT_EXCEEDED"


class SystemSettingsNotFoundException(NotFoundException):
    def __init__(self, key: Any = None) -> None:
        super().__init__("SystemSettings", key)


class EventNotFoundException(NotFoundException):
    def __init__(self, event_id: Any = None) -> None:
        super().__init__("Event", event_id)
