from __future__ import annotations

import asyncio
import json
from collections import defaultdict

import redis.asyncio as aioredis

from app.core.config import settings


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, set] = defaultdict(set)
        self._redis = aioredis.from_url(settings.REDIS_URL)

    async def connect(self, websocket, channel: str):
        await websocket.accept()
        self._connections[channel].add(websocket)

    def disconnect(self, websocket, channel: str):
        self._connections[channel].discard(websocket)

    async def broadcast(self, channel: str, message: dict):
        dead = []
        for ws in self._connections.get(channel, set()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[channel].discard(ws)

    async def publish(self, channel: str, message: dict):
        await self._redis.publish(channel, json.dumps(message))

    async def subscribe_loop(self, channel: str):
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    data = json.loads(msg["data"])
                    await self.broadcast(channel, data)
        finally:
            await pubsub.unsubscribe(channel)


ws_manager = WebSocketManager()
