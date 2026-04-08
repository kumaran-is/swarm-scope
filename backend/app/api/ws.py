"""WebSocket endpoint for live simulation streaming."""

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# In-memory subscriber map: simulation_id -> set of WebSockets
_subscribers: dict[str, set[WebSocket]] = {}


def get_subscribers(simulation_id: str) -> set[WebSocket]:
    return _subscribers.get(simulation_id, set())


async def broadcast(simulation_id: str, message: dict[str, Any]) -> None:
    """Broadcast a message to all WebSocket subscribers for a simulation."""
    sockets = list(_subscribers.get(simulation_id, set()))
    if not sockets:
        return
    data = json.dumps(message)
    disconnected = []
    for ws in sockets:
        try:
            await ws.send_text(data)
        except Exception as exc:
            logger.debug("WebSocket send failed, removing client: %s", exc)
            disconnected.append(ws)
    for ws in disconnected:
        _subscribers.get(simulation_id, set()).discard(ws)


@router.websocket("/ws/simulations/{simulation_id}")
async def simulation_ws(websocket: WebSocket, simulation_id: str):
    """
    WebSocket endpoint for live simulation events.
    Message format: {"type": "...", "tick": N, "data": {...}}
    """
    await websocket.accept()
    _subscribers.setdefault(simulation_id, set()).add(websocket)
    logger.info("WebSocket connected for simulation %s", simulation_id)

    try:
        while True:
            # Keep connection alive — client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for simulation %s", simulation_id)
    finally:
        _subscribers.get(simulation_id, set()).discard(websocket)
        if not _subscribers.get(simulation_id):
            _subscribers.pop(simulation_id, None)
