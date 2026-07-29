"""
Redis Event Publisher — Task 1.

Serializes LiveEvent payloads and publishes them to Redis channels.
Reuses the existing redis_manager singleton — no new connection is created.
"""
from loguru import logger

from app.events.schemas import LiveEvent
from app.utils.redis_manager import redis_manager


class EventPublisher:
    """
    Thin stateless wrapper around redis_manager.publish().

    Design principles:
    - Zero state — reuses the shared Redis connection pool
    - Never raises — publish failures are logged but swallowed so the
      application never crashes due to a Redis hiccup
    - Supports future scaling to 100+ cameras (all async, non-blocking)
    """

    async def publish(self, channel: str, event: LiveEvent) -> None:
        """
        Serialize ``event`` to JSON and publish it on ``channel``.

        Args:
            channel: Redis channel name (use constants from app.common.constants).
            event:   LiveEvent instance to publish.

        Failures are logged at ERROR level and silently swallowed.
        """
        try:
            json_payload = event.to_json()
            subscribers = await redis_manager.publish(channel, json_payload)
            logger.debug(
                "Event published | channel={ch} | type={t} | subscribers={s}",
                ch=channel,
                t=event.event_type,
                s=subscribers,
            )
        except Exception as exc:
            logger.error(
                "Event publish failed | channel={ch} | type={t} | error={err}",
                ch=channel,
                t=event.event_type,
                err=str(exc),
            )


# ─── Singleton ────────────────────────────────────────────────────────────────

event_publisher: EventPublisher = EventPublisher()
