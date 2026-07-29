"""WebSocket connection manager with room-based broadcasting."""
import asyncio
from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket
from loguru import logger


class WebSocketManager:
    """
    Manages WebSocket connections organized into rooms.
    Thread-safe with asyncio locks.
    No AI data is sent in Phase 1 — infrastructure only.

    Usage:
        await manager.connect(websocket, room_id="dashboard")
        await manager.broadcast_to_room("dashboard", {"type": "ping"})
        manager.disconnect(websocket, room_id="dashboard")
    """

    def __init__(self) -> None:
        # room_id -> set of connected WebSocket clients
        self._rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        """Accept a WebSocket connection and add it to a room."""
        await websocket.accept()
        async with self._lock:
            self._rooms[room_id].add(websocket)
        logger.info(
            "WS connected | room={room} | total={total}",
            room=room_id,
            total=self.connection_count(room_id),
        )

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """Remove a WebSocket from a room."""
        self._rooms[room_id].discard(websocket)
        if not self._rooms[room_id]:
            del self._rooms[room_id]
        logger.info(
            "WS disconnected | room={room} | remaining={remaining}",
            room=room_id,
            remaining=self.connection_count(room_id),
        )

    async def broadcast_to_room(
        self, room_id: str, message: dict
    ) -> int:
        """
        Send a JSON message to all clients in a room.
        Returns the number of clients that received the message.
        Automatically removes stale connections.
        """
        stale: Set[WebSocket] = set()
        sent = 0

        async with self._lock:
            connections = set(self._rooms.get(room_id, set()))

        for ws in connections:
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                stale.add(ws)

        # Clean up stale connections
        async with self._lock:
            for ws in stale:
                self._rooms[room_id].discard(ws)

        return sent

    async def broadcast_all(self, message: dict) -> int:
        """Send a JSON message to all connected clients across all rooms."""
        total_sent = 0
        async with self._lock:
            room_ids = list(self._rooms.keys())
        for room_id in room_ids:
            total_sent += await self.broadcast_to_room(room_id, message)
        return total_sent

    async def send_personal(
        self, websocket: WebSocket, message: dict
    ) -> None:
        """Send a message to a specific WebSocket client."""
        await websocket.send_json(message)

    def connection_count(self, room_id: str) -> int:
        """Return number of connections in a room."""
        return len(self._rooms.get(room_id, set()))

    @property
    def total_connections(self) -> int:
        """Return total connections across all rooms."""
        return sum(len(conns) for conns in self._rooms.values())

    @property
    def active_rooms(self) -> list:
        """Return list of room IDs with at least one connection."""
        return list(self._rooms.keys())


# Global singleton
ws_manager = WebSocketManager()
