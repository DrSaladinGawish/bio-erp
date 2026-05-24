import asyncio
import json
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket Alerts"])

_active_connections: list[WebSocket] = []


async def _redis_listener():
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
        pubsub = r.pubsub()
        await pubsub.subscribe("variance_alerts")
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                dead = []
                for conn in _active_connections:
                    try:
                        await conn.send_json(data)
                    except Exception:
                        dead.append(conn)
                for conn in dead:
                    _active_connections.remove(conn)
    except Exception:
        pass


_listener_task: asyncio.Task | None = None


@router.websocket("/ws/alerts")
async def alert_websocket(websocket: WebSocket):
    global _listener_task
    await websocket.accept()
    _active_connections.append(websocket)

    if _listener_task is None or _listener_task.done():
        _listener_task = asyncio.create_task(_redis_listener())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _active_connections.remove(websocket)
