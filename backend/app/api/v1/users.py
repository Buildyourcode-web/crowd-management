"""User management API endpoints."""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse, PagedResponse
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user.user_service import UserService
from app.utils.pagination import get_pagination, PaginationParams

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.post(
    "",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
async def create_user(
    data: UserCreate,
    request: Request,
    service: UserService = Depends(get_service),
):
    user = await service.create_user(data)
    return ApiResponse.created(
        data=UserResponse.model_validate(user),
        message="User created successfully",
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "",
    response_model=PagedResponse[UserResponse],
    summary="List users",
)
async def list_users(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination),
    service: UserService = Depends(get_service),
):
    users = await service.list_users(skip=pagination.offset, limit=pagination.page_size)
    total = await service.count_users()
    return PagedResponse.build(
        data=[UserResponse.model_validate(u) for u in users],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Get user",
)
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    service: UserService = Depends(get_service),
):
    user = await service.get_user(user_id)
    return ApiResponse.ok(
        data=UserResponse.model_validate(user),
        request_id=getattr(request.state, "request_id", None),
    )


@router.put(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Update user",
)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    request: Request,
    service: UserService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    user = await service.update_user(user_id, data)
    return ApiResponse.ok(
        data=UserResponse.model_validate(user),
        message="User updated",
        request_id=getattr(request.state, "request_id", None),
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
)
async def delete_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    await service.delete_user(user_id)
