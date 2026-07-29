"""Authentication dependency placeholder.

Full JWT authentication and RBAC will be implemented in Phase 6.
This placeholder allows routes to be protected now with minimal overhead.
"""
from typing import Optional

from fastapi import Header
from loguru import logger


async def get_current_user(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
    x_user_name: Optional[str] = Header(default=None, alias="X-User-Name"),
) -> dict:
    """
    Placeholder authentication dependency.
    In Phase 6, this will validate a Bearer JWT token and return a User model.
    For now, it reads optional identity headers for audit logging purposes.
    """
    return {
        "user_id": x_user_id or "anonymous",
        "username": x_user_name or "anonymous",
    }
