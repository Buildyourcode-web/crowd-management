"""WebSocket endpoint definitions."""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.config.settings import settings
from app.websocket.manager import ws_manager

router = APIRouter()


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """
    Generic WebSocket endpoint.
    Clients connect to /ws/{room_id} to receive room-specific broadcasts.

    Built-in rooms:
      - dashboard   : system-wide metrics and events
      - alerts      : real-time alert notifications
      - metrics     : system resource metrics
      - camera:{id} : per-camera events (Phase 2)
      - zone:{id}   : per-zone events (Phase 2)
    """
    await ws_manager.connect(websocket, room_id)
    try:
        # Send initial handshake
        await ws_manager.send_personal(
            websocket,
            {
                "type": "connected",
                "room": room_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Connected to Temple AI Crowd Management System",
            },
        )

        # Heartbeat loop — keeps connection alive
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_HEARTBEAT_INTERVAL,
                )
                # Echo ping back as pong
                if data == "ping":
                    await ws_manager.send_personal(
                        websocket,
                        {
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
            except asyncio.TimeoutError:
                # No message received — send server heartbeat
                await ws_manager.send_personal(
                    websocket,
                    {
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "connections": ws_manager.total_connections,
                    },
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, room_id)
        logger.info("WS client disconnected | room={room}", room=room_id)
    except Exception as exc:
        logger.error("WS error | room={room} | error={e}", room=room_id, e=str(exc))
        ws_manager.disconnect(websocket, room_id)
