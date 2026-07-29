"""
Redis Event Subscriber — Tasks 2, 5, 6, 7, 9, 10, 12.

Background asyncio.Task that:
  1. Subscribes to Redis channels (camera.status / camera.health / system.events)
  2. Receives JSON events published by the EventPublisher
  3. Deserializes the payload
  4. Broadcasts to the appropriate WebSocket room(s)

Auto-reconnects with exponential back-off.
Never crashes the application — every exception is caught and logged.
"""
import asyncio
import json
from typing import Dict, List, Optional

from loguru import logger
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.common.constants import (
    REDIS_CHANNEL_CAMERA_STATUS,
    REDIS_CHANNEL_CAMERA_HEALTH,
    REDIS_CHANNEL_SYSTEM,
    REDIS_CHANNEL_PERSON_COUNT,
    REDIS_CHANNEL_QUEUE_STATUS,
    REDIS_CHANNEL_ZONE_STATUS,
    REDIS_CHANNEL_FACE_MATCH,
    WS_ROOM_DASHBOARD,
)
from app.config.settings import settings
from app.utils.redis_manager import redis_manager
from app.websocket.manager import ws_manager

# ─── Channel → WebSocket Room Routing (Task 7) ───────────────────────────────
#
# Each Redis channel maps to one or more WS rooms.
# Clients subscribed to a room only receive events for that room.
#
#   camera.status  → dashboard + camera  (status changes affect the main board
#                                         and the per-camera panel)
#   camera.health  → dashboard + camera  (health metrics same routing)
#   system.events  → dashboard + system  (system-level events)

CHANNEL_ROOM_MAP: Dict[str, List[str]] = {
    REDIS_CHANNEL_CAMERA_STATUS: [WS_ROOM_DASHBOARD, "camera"],
    REDIS_CHANNEL_CAMERA_HEALTH: [WS_ROOM_DASHBOARD, "camera"],
    REDIS_CHANNEL_SYSTEM:        [WS_ROOM_DASHBOARD, "system"],
    # Phase 4 — person count events
    REDIS_CHANNEL_PERSON_COUNT:  [WS_ROOM_DASHBOARD, "person_counter"],
    # Phase 5 — queue status events
    REDIS_CHANNEL_QUEUE_STATUS:  [WS_ROOM_DASHBOARD, "queue"],
    # Phase 6 — zone status events
    REDIS_CHANNEL_ZONE_STATUS:   [WS_ROOM_DASHBOARD, "zone"],
    # Phase 7 — face recognition match events
    REDIS_CHANNEL_FACE_MATCH:    [WS_ROOM_DASHBOARD, "face"],
}

# ─── Reconnect Tuning ─────────────────────────────────────────────────────────

_RECONNECT_INITIAL_DELAY: float = 3.0
_RECONNECT_MAX_DELAY: float = 30.0
_RECONNECT_BACKOFF: float = 2.0


class EventSubscriber:
    """
    Manages a single background asyncio.Task that listens on Redis pub/sub
    and fans out received events to WebSocket rooms.

    Usage:
        await event_subscriber.start()   # called from main.py lifespan startup
        await event_subscriber.stop()    # called from main.py lifespan shutdown
    """

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._channels: List[str] = list(CHANNEL_ROOM_MAP.keys())

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Spawn the background listener task (idempotent)."""
        if self._running:
            logger.debug("EventSubscriber already running — skipping start")
            return
        self._running = True
        self._task = asyncio.create_task(
            self._listen_loop(), name="redis-event-subscriber"
        )
        logger.info(
            "EventSubscriber started | channels={ch}", ch=self._channels
        )

    async def stop(self) -> None:
        """
        Gracefully stop the listener.
        Waits up to 5 s for the task to finish, then gives up.
        """
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info("EventSubscriber stopped")

    # ─── Internal Listen Loop ─────────────────────────────────────────────────

    async def _listen_loop(self) -> None:
        """
        Outer reconnect loop.

        On every iteration:
          1. Create a fresh dedicated Redis connection (no socket_timeout).
             PubSub MUST NOT share the main pool — the shared pool has
             socket_timeout=5 s which triggers Timeout after 5 s of silence.
          2. Subscribe to all channels.
          3. Drain messages until disconnected or _running=False.
          4. Back off and retry.
        """
        delay = _RECONNECT_INITIAL_DELAY

        while self._running:
            pubsub = None
            client: Optional[Redis] = None
            try:
                # Dedicated connection: no socket_timeout so listen() blocks
                # indefinitely waiting for the next published message.
                pool = ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=2,
                    socket_timeout=None,                  # block until message
                    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                    decode_responses=True,
                )
                client = Redis(connection_pool=pool)
                await client.ping()                       # verify connectivity
                pubsub = client.pubsub()
                await pubsub.subscribe(*self._channels)

                for ch in self._channels:
                    logger.info(
                        "Subscribed to Redis channel | channel={ch}", ch=ch
                    )

                delay = _RECONNECT_INITIAL_DELAY  # reset backoff on success

                # ── Message drain loop ────────────────────────────────────────
                async for message in pubsub.listen():
                    if not self._running:
                        break

                    if message is None:
                        continue

                    msg_type: str = message.get("type", "")
                    if msg_type != "message":
                        # Subscription confirmations, pings, etc. — skip
                        continue

                    channel: str = message.get("channel", "")
                    raw_data: str = message.get("data", "")

                    logger.debug(
                        "Event received | channel={ch}", ch=channel
                    )
                    await self._handle_message(channel, raw_data)

            except asyncio.CancelledError:
                raise  # let stop() handle this

            except (RedisConnectionError, Exception) as exc:
                logger.warning(
                    "EventSubscriber disconnected | error={err} | "
                    "reconnecting in {delay}s",
                    err=str(exc),
                    delay=delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * _RECONNECT_BACKOFF, _RECONNECT_MAX_DELAY)

            finally:
                if pubsub is not None:
                    try:
                        await pubsub.unsubscribe()
                        await pubsub.aclose()
                    except Exception:
                        pass
                if client is not None:
                    try:
                        await client.aclose()
                    except Exception:
                        pass

    # ─── Message Handler ──────────────────────────────────────────────────────

    async def _handle_message(self, channel: str, raw: str) -> None:
        """
        Deserialize a raw JSON string and broadcast to mapped WebSocket rooms.

        Tasks covered: 5, 6, 7, 9, 10
        - Only JSON payloads are forwarded (Task 6)
        - Routed to specific rooms based on channel (Task 7)
        - WS broadcast errors are caught and logged (Task 10)
        """
        # ── Deserialize ───────────────────────────────────────────────────────
        try:
            payload: dict = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Invalid JSON on channel={ch} | error={err}",
                ch=channel,
                err=str(exc),
            )
            return

        # ── Route to WebSocket rooms ──────────────────────────────────────────
        rooms = CHANNEL_ROOM_MAP.get(channel, [WS_ROOM_DASHBOARD])
        event_type = payload.get("event_type", "unknown")

        for room in rooms:
            try:
                sent = await ws_manager.broadcast_to_room(room, payload)
                if sent > 0:
                    logger.info(
                        "Event broadcast | room={room} | type={t} | clients={n}",
                        room=room,
                        t=event_type,
                        n=sent,
                    )
                else:
                    logger.debug(
                        "Event broadcast — no clients in room | room={room} | type={t}",
                        room=room,
                        t=event_type,
                    )
            except Exception as exc:
                logger.error(
                    "WS broadcast error | room={room} | type={t} | error={err}",
                    room=room,
                    t=event_type,
                    err=str(exc),
                )


# ─── Singleton ────────────────────────────────────────────────────────────────

event_subscriber: EventSubscriber = EventSubscriber()
