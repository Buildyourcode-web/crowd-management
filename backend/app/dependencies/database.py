"""Database session dependency."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db

__all__ = ["get_db"]
