"""Standardized API response models."""
from datetime import datetime, timezone
from math import ceil
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard success response envelope."""

    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def ok(
        cls,
        data: Optional[T] = None,
        message: str = "Operation completed successfully",
        request_id: Optional[str] = None,
    ) -> "ApiResponse[T]":
        return cls(success=True, message=message, data=data, request_id=request_id)

    @classmethod
    def created(
        cls,
        data: Optional[T] = None,
        message: str = "Resource created successfully",
        request_id: Optional[str] = None,
    ) -> "ApiResponse[T]":
        return cls(success=True, message=message, data=data, request_id=request_id)


class ErrorDetail(BaseModel):
    error_code: str
    message: str
    detail: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    success: bool = False
    error: ErrorDetail
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_exception(
        cls,
        error_code: str,
        message: str,
        detail: Optional[Any] = None,
        request_id: Optional[str] = None,
    ) -> "ErrorResponse":
        return cls(
            error=ErrorDetail(error_code=error_code, message=message, detail=detail),
            request_id=request_id,
        )


class PageMeta(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PagedResponse(BaseModel, Generic[T]):
    """Paginated list response."""

    success: bool = True
    message: str = "Data fetched successfully"
    data: List[T]
    meta: PageMeta
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def build(
        cls,
        data: List[T],
        page: int,
        page_size: int,
        total: int,
        request_id: Optional[str] = None,
    ) -> "PagedResponse[T]":
        total_pages = max(1, ceil(total / page_size))
        return cls(
            data=data,
            meta=PageMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
            request_id=request_id,
        )
