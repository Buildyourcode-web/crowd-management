"""Global FastAPI exception handlers — converts all errors to structured JSON."""
import traceback
from typing import Union

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.exceptions import AppException
from app.common.response import ErrorResponse
from app.core.logging import get_request_id


def _extract_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", get_request_id())


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    request_id = _extract_request_id(request)
    logger.warning(
        "AppException | rid={rid} | code={code} | msg={msg}",
        rid=request_id,
        code=exc.error_code,
        msg=exc.message,
    )
    body = ErrorResponse.from_exception(
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.http_status, content=body.model_dump(mode="json"))


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    request_id = _extract_request_id(request)
    logger.warning(
        "HTTPException | rid={rid} | status={status} | detail={detail}",
        rid=request_id,
        status=exc.status_code,
        detail=exc.detail,
    )
    body = ErrorResponse.from_exception(
        error_code="HTTP_ERROR",
        message=str(exc.detail),
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    request_id = _extract_request_id(request)
    errors = exc.errors() if hasattr(exc, "errors") else [{"msg": str(exc)}]
    logger.warning(
        "ValidationError | rid={rid} | errors={errors}",
        rid=request_id,
        errors=errors,
    )
    body = ErrorResponse.from_exception(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        detail=errors,
        request_id=request_id,
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = _extract_request_id(request)
    logger.error(
        "UnhandledException | rid={rid} | type={t} | msg={msg}\n{tb}",
        rid=request_id,
        t=type(exc).__name__,
        msg=str(exc),
        tb=traceback.format_exc(),
    )
    body = ErrorResponse.from_exception(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        request_id=request_id,
    )
    return JSONResponse(status_code=500, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app instance."""
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
