"""Request logging middleware — attaches request ID and logs all requests."""
import time
import uuid

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.common.constants import HEADER_REQUEST_ID, HEADER_API_VERSION
from app.config.settings import settings
from app.core.logging import set_request_id


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Generates or propagates a request ID
    2. Sets it on request.state and the logging context variable
    3. Adds X-Request-ID and X-API-Version headers to every response
    4. Logs method, path, status code, and duration
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or reuse request ID from incoming header
        request_id = request.headers.get(HEADER_REQUEST_ID) or str(uuid.uuid4())
        request.state.request_id = request_id
        set_request_id(request_id)

        start_time = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        # Attach correlation headers to response
        response.headers[HEADER_REQUEST_ID] = request_id
        response.headers[HEADER_API_VERSION] = settings.APP_VERSION

        # Skip logging for health check noise in production
        if not (request.url.path.startswith("/health") and not settings.DEBUG):
            logger.info(
                "{method} {path} | status={status} | {duration}ms | rid={rid}",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration=duration_ms,
                rid=request_id,
            )

        return response
