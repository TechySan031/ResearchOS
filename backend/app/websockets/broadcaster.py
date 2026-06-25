from __future__ import annotations

import asyncio
import json
import logging

from app.integrations.redis_client import RedisManager
from app.websockets.connection_manager import manager

logger = logging.getLogger(__name__)

CHANNEL_PREFIX_PROJECT = "ws:project:"
CHANNEL_GLOBAL = "ws:global"


class RedisSubscriberTask:
    def __init__(self):
        self.redis = RedisManager()
        self.task = None
        self.running = False

    async def start(self):
        self.running = True

        await self.redis.connect()

        self.task = asyncio.create_task(
            self._listen(),
            name="redis-websocket-subscriber",
        )

        logger.info("Redis websocket subscriber started")

    async def stop(self):
        self.running = False

        if self.task:
            self.task.cancel()

        logger.info("Redis websocket subscriber stopped")

    async def _listen(self):
        while self.running:
            try:
                pubsub = await self.redis.subscribe(CHANNEL_GLOBAL)

                if not pubsub:
                    await asyncio.sleep(5)
                    continue

                async for message in pubsub.listen():

                    if message["type"] != "message":
                        continue

                    payload = json.loads(message["data"])

                    await manager.broadcast_all(payload)

            except Exception as exc:
                logger.error(f"Redis subscriber crashed: {exc}")
                await asyncio.sleep(5)


async def publish_global(payload: dict):
    redis = RedisManager()

    await redis.connect()

    await redis.publish(
        CHANNEL_GLOBAL,
        payload,
    )


broadcaster_task = RedisSubscriberTask()