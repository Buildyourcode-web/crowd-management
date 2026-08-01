"""Async Redis client manager."""
import time
from typing import Any, Optional

from loguru import logger
from redis.asyncio import Redis, ConnectionPool
from redis.asyncio.client import PubSub
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.common.exceptions import RedisConnectionException
from app.config.settings import settings


class RedisManager:
    """
    Async Redis client wrapper.
    Manages connection lifecycle and provides get/set/delete/publish/subscribe.
    pub/sub infrastructure is ready — implementation happens in Phase 2.
    """

    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def connect(self) -> None:
        """Create the Redis connection pool and verify connectivity."""
        try:
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                decode_responses=True,
            )
            self._client = Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info("Redis connected | url={url}", url=settings.REDIS_URL)
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.critical("Redis connection failed: {e}", e=str(exc))
            raise RedisConnectionException(detail=str(exc)) from exc

    async def disconnect(self) -> None:
        """Close all Redis connections."""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.aclose()
        logger.info("Redis connection closed")

    @property
    def client(self) -> Redis:
        if not self._client:
            raise RedisConnectionException(detail="Redis client not initialized")
        return self._client

    @property
    def is_connected(self) -> bool:
        """True when Redis client is initialized."""
        return self._client is not None

    # ── Health ────────────────────────────────────────────────────────────────

    async def ping(self) -> dict:
        """Ping Redis and return latency + status."""
        start = time.monotonic()
        try:
            await self.client.ping()
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            return {"status": "healthy", "latency_ms": latency_ms}
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            logger.error("Redis ping failed: {e}", e=str(exc))
            raise RedisConnectionException(detail=str(exc)) from exc

    # ── Basic Key-Value ───────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[str]:
        """Get a string value by key."""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
    ) -> bool:
        """Set a key with optional expiry in seconds."""
        return await self.client.set(key, str(value), ex=ex)  # type: ignore[return-value]

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns count of deleted keys."""
        return await self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return bool(await self.client.exists(key))

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on a key."""
        return await self.client.expire(key, seconds)

    async def incr(self, key: str, amount: int = 1) -> int:
        """Atomically increment a counter."""
        return await self.client.incr(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """Atomically decrement a counter."""
        return await self.client.decr(key, amount)

    # ── Pub/Sub Infrastructure (Phase 2 implementation) ───────────────────────

    async def publish(self, channel: str, message: str) -> int:
        """
        Publish a message to a Redis channel.
        Infrastructure ready — used in Phase 2 for real-time AI data propagation.
        Returns the number of subscribers that received the message.
        """
        return await self.client.publish(channel, message)

    def pubsub(self) -> PubSub:
        """
        Create a PubSub object for subscribing to channels.
        Infrastructure ready — subscription loops implemented in Phase 2.
        """
        return self.client.pubsub()

    async def subscribe(self, *channels: str) -> PubSub:
        """
        Subscribe to one or more channels and return the PubSub handle.
        Infrastructure ready — message handling implemented in Phase 2.
        """
        ps = self.client.pubsub()
        await ps.subscribe(*channels)
        logger.debug("Subscribed to channels: {c}", c=channels)
        return ps


# Global singleton instance
redis_manager = RedisManager()
