"""Redis-backed asynchronous event bus for agent coordination.

Provides pub/sub over Redis channels so that agents, the orchestrator, and
WebSocket endpoints can communicate in real-time.  When Redis is not available
the bus logs a warning and silently drops messages instead of crashing the
application.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, AsyncGenerator

import structlog

from app.core.constants import AgentName

logger = structlog.stdlib.get_logger(__name__)

# ── Data Structures ──────────────────────────────────────────────────────────

AGENT_EVENTS_CHANNEL = "researchos:agent_events"
_LOCAL_SUBSCRIBERS: list[asyncio.Queue[AgentEvent]] = []
_bus: EventBus | None = None


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """Immutable record describing a single agent lifecycle event.

    Attributes:
        project_id: UUID of the research project.
        agent_name: Which agent emitted the event.
        event_type: Lifecycle phase (started, progress, completed, failed, warning).
        data: Arbitrary payload carried with the event.
        timestamp: UNIX epoch seconds (float) when the event was created.
        event_id: Unique identifier for this event instance.
    """

    project_id: str
    agent_name: str
    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_json(self) -> str:
        """Serialize the event to a JSON string."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str | bytes) -> "AgentEvent":
        """Deserialize an event from a JSON string or bytes."""
        payload = json.loads(raw)
        return cls(**payload)


# ── Event Bus ────────────────────────────────────────────────────────────────


class EventBus:
    """Thin wrapper around Redis Pub/Sub for agent event streaming.

    Provides an in-memory pub-sub fallback when Redis is not available,
    ensuring real-time updates still work in degraded mode.

    Args:
        redis_client: An ``redis.asyncio.Redis`` instance (or ``None``).
        channel: Redis channel name used for all agent events.
    """

    def __init__(
        self,
        redis_client: Any | None = None,
        channel: str = AGENT_EVENTS_CHANNEL,
    ) -> None:
        self._redis = redis_client
        self._channel = channel
        self._local_subscribers = _LOCAL_SUBSCRIBERS

    @property
    def redis(self) -> Any | None:
        """Dynamically resolve the active Redis client."""
        if self._redis is not None:
            return self._redis
        from app.integrations.redis_client import RedisManager
        mgr = RedisManager()
        if mgr.is_connected:
            return mgr._client
        return None

    # ── Publishing ───────────────────────────────────────────────────────

    async def publish(self, event: AgentEvent) -> int:
        """Publish an ``AgentEvent`` onto the Redis channel or local queues.

        Returns:
            Number of subscribers that received the message.
        """
        redis_client = self.redis
        if redis_client is None:
            logger.warning(
                "event_bus.publish.no_redis",
                event_id=event.event_id,
                agent=event.agent_name,
                msg="Falling back to local in-memory pub/sub",
            )
            # In-memory local fallback
            count = 0
            for q in list(self._local_subscribers):
                try:
                    q.put_nowait(event)
                    count += 1
                except Exception:
                    pass
            return count

        try:
            receivers: int = await asyncio.wait_for(
                redis_client.publish(
                    self._channel,
                    event.to_json(),
                ),
                timeout=5.0
            )
            logger.debug(
                "event_bus.published",
                event_id=event.event_id,
                agent=event.agent_name,
                event_type=event.event_type,
                receivers=receivers,
            )
            return receivers
        except asyncio.TimeoutError:
            logger.error(
                "event_bus.publish.timeout",
                event_id=event.event_id,
                agent=event.agent_name,
                timeout=5.0,
            )
            return 0
        except Exception:
            logger.exception(
                "event_bus.publish.error",
                event_id=event.event_id,
                agent=event.agent_name,
            )
            return 0

    # ── Subscribing ──────────────────────────────────────────────────────

    async def subscribe(
        self,
        *,
        project_id: str | None = None,
        agent_name: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Yield ``AgentEvent`` objects as they arrive on the channel.

        Optionally filter by ``project_id`` and/or ``agent_name`` so that
        consumers only see events relevant to them.

        Yields:
            AgentEvent instances matching the optional filters.
        """
        redis_client = self.redis
        if redis_client is None:
            logger.warning(
                "event_bus.subscribe.no_redis",
                msg="Falling back to local in-memory subscription",
            )
            q = asyncio.Queue()
            self._local_subscribers.append(q)
            try:
                while True:
                    event = await q.get()
                    # Apply optional filters
                    if project_id and event.project_id != project_id:
                        continue
                    if agent_name and event.agent_name != agent_name:
                        continue
                    yield event
            except asyncio.CancelledError:
                logger.info("event_bus.subscribe.local_cancelled")
            finally:
                if q in self._local_subscribers:
                    self._local_subscribers.remove(q)
            return

        pubsub = redis_client.pubsub()
        try:
            await pubsub.subscribe(self._channel)
            logger.info(
                "event_bus.subscribed",
                channel=self._channel,
                project_filter=project_id,
                agent_filter=agent_name,
            )

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message is None:
                    await asyncio.sleep(0.05)
                    continue

                raw_data = message.get("data")
                if raw_data is None:
                    continue

                try:
                    event = AgentEvent.from_json(raw_data)
                except (json.JSONDecodeError, TypeError, KeyError):
                    logger.warning(
                        "event_bus.subscribe.bad_message",
                        raw=str(raw_data)[:200],
                    )
                    continue

                # Apply optional filters
                if project_id and event.project_id != project_id:
                    continue
                if agent_name and event.agent_name != agent_name:
                    continue

                yield event
        except asyncio.CancelledError:
            logger.info("event_bus.subscribe.cancelled")
        except Exception:
            logger.exception("event_bus.subscribe.error")
        finally:
            await pubsub.unsubscribe(self._channel)
            await pubsub.close()


# ── Module-Level Helpers ─────────────────────────────────────────────────────

_bus: EventBus | None = None


def init_event_bus(redis_client: Any | None = None) -> EventBus:
    global _bus
    _bus = EventBus(redis_client=redis_client)
    return _bus
    
def get_event_bus() -> EventBus:
    global _bus

    if _bus is None:
        _bus = EventBus()

    return _bus


async def publish_agent_event(
    project_id: str,
    agent_name: str | AgentName,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> int:
    """Convenience helper to publish an agent event via the global bus.

    Args:
        project_id: UUID string of the research project.
        agent_name: Agent that is emitting the event.
        event_type: Lifecycle phase (e.g. ``started``, ``completed``).
        data: Optional payload dict.

    Returns:
        Number of subscribers that received the message.
    """
    event = AgentEvent(
        project_id=project_id,
        agent_name=str(agent_name),
        event_type=event_type,
        data=data or {},
    )
    bus = get_event_bus()
    return await bus.publish(event)


async def subscribe_agent_events(
    *,
    project_id: str | None = None,
    agent_name: str | None = None,
) -> AsyncGenerator[AgentEvent, None]:
    """Convenience helper to subscribe to agent events via the global bus.

    Args:
        project_id: Only yield events for this project (optional).
        agent_name: Only yield events from this agent (optional).

    Yields:
        ``AgentEvent`` objects matching the filters.
    """
    bus = get_event_bus()
    async for event in bus.subscribe(
        project_id=project_id,
        agent_name=agent_name,
    ):
        yield event
