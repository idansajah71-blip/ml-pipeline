import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Optional
from fastapi import WebSocket
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._pubsub_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]

    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            dead = set()
            for ws in self.active_connections[channel]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                self.active_connections[channel].discard(ws)

    async def send_personal(self, channel: str, message: dict):
        """Send to all connections on a channel."""
        await self.broadcast(channel, message)

    async def start_redis_listener(self):
        try:
            self._pubsub_task = asyncio.create_task(self._listen_redis())
        except Exception as e:
            logger.error(f"Redis listener start error: {e}")

    async def _listen_redis(self):
        try:
            import redis.asyncio as redis

            client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )

            pubsub = client.pubsub()
            await pubsub.psubscribe("training:*", "scrape:*")

            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    await self.broadcast(channel, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    async def stop_redis_listener(self):
        if self._pubsub_task:
            self._pubsub_task.cancel()


manager = ConnectionManager()


async def emit_scrape_progress(job_id: str, event: str, data: dict):
    """Emit scrape progress event via Redis pub/sub."""
    try:
        import redis.asyncio as redis
        client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        payload = {
            "event": event,
            "job_id": job_id,
            **data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await client.publish(f"scrape:{job_id}", json.dumps(payload, default=str))
        await client.aclose()
    except Exception:
        pass
