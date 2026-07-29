"""Structured logging via Loguru with two file sinks and per-request correlation IDs."""
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Optional

from loguru import logger

from app.config.settings import settings
from app.common.constants import LOG_FORMAT_CONSOLE, LOG_FORMAT_FILE

# Per-request correlation stored in a context variable
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current request ID, generating one if absent."""
    rid = _request_id_var.get()
    if not rid:
        rid = str(uuid.uuid4())
        _request_id_var.set(rid)
    return rid


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set (or generate) the request ID for the current async context."""
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def setup_logging() -> None:
    """Configure all Loguru sinks. Must be called once at startup."""
    logger.remove()  # Remove the default stderr handler

    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # ── Console sink ─────────────────────────────────────────────────────────
    logger.add(
        sys.stdout,
        format=LOG_FORMAT_CONSOLE,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
        enqueue=True,
    )

    # ── Application log ───────────────────────────────────────────────────────
    logger.add(
        str(log_dir / "application.log"),
        format=LOG_FORMAT_FILE,
        level="INFO",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="gz",
        enqueue=True,
        diagnose=False,
    )

    # ── Error log ─────────────────────────────────────────────────────────────
    logger.add(
        str(log_dir / "error.log"),
        format=LOG_FORMAT_FILE,
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="gz",
        enqueue=True,
        diagnose=True,
        backtrace=True,
    )

    # Bind default context variables so they always exist
    logger.configure(extra={"request_id": ""})

    logger.info(
        "Logging configured | env={env} | debug={debug} | log_dir={log_dir}",
        env=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        log_dir=str(log_dir),
    )


def get_logger(name: str):
    """Return a named logger bound with the given module name."""
    return logger.bind(name=name)
