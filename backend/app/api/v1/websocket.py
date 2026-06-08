"""
ResearchOS — WebSocket Endpoint

Real-time bidirectional communication for agent status updates,
workflow progress, and streaming LLM output.

Supports multiple concurrent clients per project via ConnectionManager.
"""

import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.events import EventBus, publish_agent_event, subscribe_agent_events
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections per project.

    Supports multiple concurrent clients subscribed to the same project.
    Handles connection lifecycle, broadcasting, and cleanup.
    """

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, project_id: str, websocket: WebSocket):
        """Accept and register a WebSocket connection for a project."""
        await websocket.accept()
        async with self._lock:
            if project_id not in self._connections:
                self._connections[project_id] = set()
            self._connections[project_id].add(websocket)

        logger.info(
            "websocket_connected",
            project_id=project_id,
            total_connections=len(self._connections.get(project_id, set())),
        )

    async def disconnect(self, project_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if project_id in self._connections:
                self._connections[project_id].discard(websocket)
                if not self._connections[project_id]:
                    del self._connections[project_id]

        logger.info("websocket_disconnected", project_id=project_id)

    async def broadcast(self, project_id: str, message: dict):
        """
        Send a message to all WebSocket clients subscribed to a project.

        Failed sends (broken connections) are cleaned up automatically.
        """
        connections = self._connections.get(project_id, set()).copy()
        dead_connections = set()

        for connection in connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    "websocket_send_failed",
                    project_id=project_id,
                    error=str(e),
                )
                dead_connections.add(connection)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                if project_id in self._connections:
                    self._connections[project_id] -= dead_connections

    def get_connection_count(self, project_id: str) -> int:
        """Get number of active connections for a project."""
        return len(self._connections.get(project_id, set()))

    def get_all_projects(self) -> list[str]:
        """Get list of project IDs with active connections."""
        return list(self._connections.keys())


# Global connection manager singleton
manager = ConnectionManager()


async def _relay_agent_events(project_id: str):
    """
    Background task that relays Redis pub-sub agent events to
    WebSocket clients for a specific project.

    Runs until no clients are connected or an error occurs.
    """
    try:
        async for event in subscribe_agent_events(project_id=project_id):
            if manager.get_connection_count(project_id) == 0:
                logger.info(
                    "stopping_event_relay_no_clients",
                    project_id=project_id,
                )
                break

            await manager.broadcast(project_id, {
                "type": event.event_type,
                "agent": event.agent_name,
                "data": event.data,
                "timestamp": event.timestamp,
                "project_id": project_id,
            })
    except asyncio.CancelledError:
        logger.info("event_relay_cancelled", project_id=project_id)
    except Exception as e:
        logger.error(
            "event_relay_error",
            project_id=project_id,
            error=str(e),
        )


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time project updates.

    Client → Server messages:
        {"type": "subscribe", "project_id": "..."}
        {"type": "ping"}
        {"type": "user_input", "agent": "...", "data": {...}}

    Server → Client messages:
        {"type": "agent_started", "agent": "...", "timestamp": "..."}
        {"type": "agent_progress", "agent": "...", "progress": 0.45, "data": {...}}
        {"type": "agent_completed", "agent": "...", "data": {...}}
        {"type": "agent_error", "agent": "...", "error": "..."}
        {"type": "workflow_status", "status": "...", "current_agent": "..."}
        {"type": "stream_token", "agent": "...", "token": "..."}
        {"type": "pong"}
    """
    await manager.connect(project_id, websocket)

    # Start background relay for Redis agent events
    relay_task = asyncio.create_task(_relay_agent_events(project_id))

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "project_id": project_id,
            "message": "Connected to ResearchOS agent event stream",
        })

        while True:
            # Wait for client messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "subscribe":
                    # Already subscribed via URL — acknowledge
                    await websocket.send_json({
                        "type": "subscribed",
                        "project_id": project_id,
                    })

                elif msg_type == "user_input":
                    # Forward user input to the event bus for agent consumption
                    await publish_agent_event(
                        project_id=project_id,
                        agent_name=message.get("agent", "user"),
                        event_type="user_input",
                        data=message.get("data", {}),
                    )
                    await websocket.send_json({
                        "type": "input_received",
                        "agent": message.get("agent", "user"),
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        logger.info("websocket_client_disconnected", project_id=project_id)
    except Exception as e:
        logger.error(
            "websocket_error",
            project_id=project_id,
            error=str(e),
        )
    finally:
        relay_task.cancel()
        try:
            await relay_task
        except asyncio.CancelledError:
            pass
        await manager.disconnect(project_id, websocket)
