"""Redis dependency."""
from app.utils.redis_manager import redis_manager
from redis.asyncio import Redis


async def get_redis() -> Redis:
    """Return the application Redis client."""
    return redis_manager.client
