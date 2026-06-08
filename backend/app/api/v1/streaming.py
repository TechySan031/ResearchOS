"""
ResearchOS — Server-Sent Events (SSE) Streaming Endpoint

Provides unidirectional token-by-token streaming from LLM agents
to frontend clients.  Uses SSE (text/event-stream) which is simpler
than WebSocket for unidirectional content delivery and reconnects
automatically via the browser-native EventSource API.

The existing WebSocket endpoint handles bidirectional control messages.
This SSE endpoint handles content streaming only.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.events import get_event_bus, AgentEvent
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

HEARTBEAT_INTERVAL_SECONDS = 15


async def _sse_event_generator(
    request: Request,
    project_id: str,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events for a specific project.

    Subscribes to the global event bus and forwards ``stream_token``,
    ``agent_started``, ``agent_completed``, and ``agent_error`` events
    to the connected client.

    Includes periodic heartbeat comments to keep the connection alive
    through proxies and load balancers.
    """
    bus = get_event_bus()
    queue: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=1000)

    logger.info(
        "sse.connected",
        project_id=project_id,
    )

    try:
        # Register inside try so finally always cleans up
        bus._local_subscribers.append(queue)

        # Send initial connection event
        yield _format_sse("connected", {"project_id": project_id})
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("sse.client_disconnected", project_id=project_id)
                break

            try:
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                # Send heartbeat comment to keep connection alive
                yield ": heartbeat\n\n"
                continue

            # Filter to this project only
            if event.project_id != project_id:
                continue

            # Forward relevant event types
            if event.event_type in (
                "stream_token",
                "agent_started",
                "agent_completed",
                "agent_error",
                "workflow_completed",
                "workflow_failed",
            ):
                yield _format_sse(event.event_type, {
                    "agent": event.agent_name,
                    "data": event.data,
                    "timestamp": event.timestamp,
                })

    except asyncio.CancelledError:
        logger.info("sse.cancelled", project_id=project_id)
    except Exception:
        logger.exception("sse.error", project_id=project_id)
    finally:
        # Clean up the subscriber (safe against concurrent modification)
        try:
            bus._local_subscribers.remove(queue)
        except ValueError:
            pass
        logger.info("sse.disconnected", project_id=project_id)


def _format_sse(event_type: str, data: dict) -> str:
    """Format a single SSE message.

    SSE format:
        event: <type>
        data: <json>
        \\n
    """
    json_data = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"


@router.get("/stream")
async def stream_events(
    request: Request,
    project_id: str,
):
    """SSE endpoint for streaming LLM tokens and agent events.

    Connect via ``EventSource`` in the browser::

        const es = new EventSource('/api/v1/projects/<id>/stream');
        es.addEventListener('stream_token', (e) => {
            const { data } = JSON.parse(e.data);
            // data.token contains the LLM token
        });
        es.addEventListener('agent_completed', (e) => { ... });

    Events emitted:
        ``stream_token``       — individual LLM token
        ``agent_started``      — agent began execution
        ``agent_completed``    — agent finished successfully
        ``agent_error``        — agent encountered an error
        ``workflow_completed`` — entire workflow finished
        ``workflow_failed``    — workflow failed
    """
    return StreamingResponse(
        _sse_event_generator(request, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
