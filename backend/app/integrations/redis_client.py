"""Redis client wrapper with connection pooling and graceful fallback.

Provides a singleton ``RedisManager`` that wraps *redis.asyncio* with:
- JSON serialization / deserialization of values.
- Automatic reconnect on transient failures.
- Pub/Sub support via ``publish`` / ``subscribe``.
- ``incr_with_ttl`` helper for sliding-window rate limiting.
- Graceful degradation — all read operations return ``None`` and all
  writes silently succeed when Redis is unavailable, with a warning
  logged on each attempt.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RedisManager:
    """Singleton async Redis manager with JSON helpers and pub/sub.

    Usage::

        mgr = RedisManager()
        await mgr.connect()
        await mgr.set("key", {"foo": "bar"}, ttl=3600)
        value = await mgr.get("key")
        await mgr.disconnect()
    """

    _instance: RedisManager | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> RedisManager:  # noqa: D102 — singleton
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore[attr-defined]
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:  # type: ignore[attr-defined]
            return
        self._initialized = True
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None
        self._connected: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish a connection pool to Redis.

        If Redis is unreachable the manager switches to a *degraded*
        mode where every operation is a graceful no-op.
        """
        if self._connected:
            return

        async with self._lock:
            if self._connected:
                return
            settings = get_settings()
            redis_url: str = settings.redis_url
            try:
                self._pool = ConnectionPool.from_url(
                    redis_url,
                    max_connections=20,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                self._client = Redis(connection_pool=self._pool)
                # Verify connectivity
                await self._client.ping()
                self._connected = True
                logger.info("redis.connected", url=redis_url)
            except (RedisConnectionError, RedisTimeoutError, OSError) as exc:
                logger.warning(
                    "redis.connection_failed",
                    url=redis_url,
                    error=str(exc),
                    msg="Running in degraded mode — cache disabled",
                )
                self._connected = False

    async def disconnect(self) -> None:
        """Close the Redis connection pool."""
        if self._client is not None:
            try:
                await self._client.aclose()
            except RedisError:
                pass
        if self._pool is not None:
            try:
                await self._pool.disconnect()
            except RedisError:
                pass
        self._client = None
        self._pool = None
        self._connected = False
        logger.info("redis.disconnected")

    @property
    def is_connected(self) -> bool:
        """Return ``True`` if Redis is currently reachable."""
        return self._connected

    # ------------------------------------------------------------------
    # Core key/value operations
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Any | None:
        """Get a JSON-deserialized value by *key*.

        Returns ``None`` when Redis is unavailable or the key does not
        exist.
        """
        if not self._connected or self._client is None:
            return None
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # Stored value is not JSON — return raw string.
            return raw
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("redis.get_failed", key=key, error=str(exc))
            self._connected = False
            return None
        except RedisError as exc:
            logger.warning("redis.get_error", key=key, error=str(exc))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Store a JSON-serialized *value* under *key*.

        Args:
            key: The cache key.
            value: Any JSON-serializable Python object.
            ttl: Time-to-live in **seconds**.  ``None`` means persist
                 until manual deletion.

        Returns:
            ``True`` on success, ``False`` when Redis is unavailable.
        """
        if not self._connected or self._client is None:
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl is not None:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
            return True
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("redis.set_failed", key=key, error=str(exc))
            self._connected = False
            return False
        except RedisError as exc:
            logger.warning("redis.set_error", key=key, error=str(exc))
            return False

    async def delete(self, key: str) -> bool:
        """Delete *key* from Redis.  Returns ``True`` if the key existed."""
        if not self._connected or self._client is None:
            return False
        try:
            result = await self._client.delete(key)
            return result > 0
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("redis.delete_failed", key=key, error=str(exc))
            self._connected = False
            return False
        except RedisError as exc:
            logger.warning("redis.delete_error", key=key, error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Rate-limiting helper
    # ------------------------------------------------------------------

    async def incr_with_ttl(self, key: str, ttl: int) -> int | None:
        """Atomically increment *key* and set its TTL on first creation.

        This is the building block for a sliding-window rate limiter:
        increment a counter keyed by ``rate:<identity>:<window>`` and
        compare the returned count against the allowed maximum.

        Args:
            key: The counter key.
            ttl: TTL in seconds (applied only on creation).

        Returns:
            The current count after increment, or ``None`` if Redis is
            unavailable.
        """
        if not self._connected or self._client is None:
            return None
        try:
            pipe = self._client.pipeline(transaction=True)
            pipe.incr(key)
            pipe.expire(key, ttl, nx=True)  # Only set TTL if not yet set
            results = await pipe.execute()
            return int(results[0])
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("redis.incr_failed", key=key, error=str(exc))
            self._connected = False
            return None
        except RedisError as exc:
            logger.warning("redis.incr_error", key=key, error=str(exc))
            return None

    # ------------------------------------------------------------------
    # Pub/Sub
    # ------------------------------------------------------------------

    async def publish(self, channel: str, message: Any) -> int | None:
        """Publish a JSON-serialized *message* to *channel*.

        Returns the number of subscribers that received the message.
        """
        if not self._connected or self._client is None:
            return None
        try:
            serialized = json.dumps(message, default=str)
            return await self._client.publish(channel, serialized)
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("redis.publish_failed", channel=channel, error=str(exc))
            self._connected = False
            return None
        except RedisError as exc:
            logger.warning("redis.publish_error", channel=channel, error=str(exc))
            return None

    async def subscribe(self, channel: str) -> aioredis.client.PubSub | None:
        """Subscribe to *channel* and return the ``PubSub`` object.

        The caller is responsible for iterating messages and
        unsubscribing::

            ps = await redis.subscribe("events")
            async for msg in ps.listen():
                if msg["type"] == "message":
                    data = json.loads(msg["data"])
                    ...
            await ps.unsubscribe(channel)
        """
        if not self._connected or self._client is None:
            return None
        try:
            pubsub = self._client.pubsub()
            await pubsub.subscribe(channel)
            logger.info("redis.subscribed", channel=channel)
            return pubsub
        except (RedisConnectionError, RedisTimeoutError) as exc:
            logger.warning("redis.subscribe_failed", channel=channel, error=str(exc))
            self._connected = False
            return None
        except RedisError as exc:
            logger.warning("redis.subscribe_error", channel=channel, error=str(exc))
            return None
