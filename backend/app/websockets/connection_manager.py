from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    websocket: WebSocket = field(repr=False)

    user_id: str = ""
    project_id: str = ""

    id: str = field(default_factory=lambda: str(uuid4()))

    connected_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    last_ping_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    def is_open(self) -> bool:
        return self.websocket.client_state == WebSocketState.CONNECTED


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocketConnection] = {}
        self._project_index: dict[str, set[str]] = defaultdict(set)
        self._user_index: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        project_id: str,
        user_id: str,
    ) -> WebSocketConnection:
        await websocket.accept()
        conn = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            project_id=project_id,
        )
        async with self._lock:
            self._connections[conn.id] = conn
            self._project_index[project_id].add(conn.id)
            self._user_index[user_id].add(conn.id)
        logger.info(
            "WebSocket connected: conn_id=%s project=%s user=%s",
            conn.id,
            project_id,
            user_id,
        )
        return conn

    async def disconnect(self, conn_id: str) -> None:
        async with self._lock:
            conn = self._connections.pop(conn_id, None)
            if conn is None:
                return
            self._project_index[conn.project_id].discard(conn_id)
            if not self._project_index[conn.project_id]:
                del self._project_index[conn.project_id]
            self._user_index[conn.user_id].discard(conn_id)
            if not self._user_index[conn.user_id]:
                del self._user_index[conn.user_id]
        logger.info("WebSocket disconnected: conn_id=%s", conn_id)

    async def send_to_connection(self, conn_id: str, payload: dict[str, Any]) -> bool:
        conn = self._connections.get(conn_id)
        if conn is None or not conn.is_open():
            return False
        try:
            await conn.websocket.send_json(payload)
            return True
        except Exception as exc:
            logger.warning("Failed to send to conn_id=%s: %s", conn_id, exc)
            await self.disconnect(conn_id)
            return False

    async def broadcast_to_project(
        self,
        project_id: str,
        payload: dict[str, Any],
    ) -> int:
        conn_ids = set(self._project_index.get(project_id, set()))
        if not conn_ids:
            return 0
        results = await asyncio.gather(
            *[self.send_to_connection(cid, payload) for cid in conn_ids],
            return_exceptions=True,
        )
        sent = sum(1 for r in results if r is True)
        return sent

    async def broadcast_to_user(
        self,
        user_id: str,
        payload: dict[str, Any],
    ) -> int:
        conn_ids = set(self._user_index.get(user_id, set()))
        if not conn_ids:
            return 0
        results = await asyncio.gather(
            *[self.send_to_connection(cid, payload) for cid in conn_ids],
            return_exceptions=True,
        )
        return sum(1 for r in results if r is True)

    async def broadcast_all(self, payload: dict[str, Any]) -> int:
        conn_ids = list(self._connections.keys())
        if not conn_ids:
            return 0
        results = await asyncio.gather(
            *[self.send_to_connection(cid, payload) for cid in conn_ids],
            return_exceptions=True,
        )
        return sum(1 for r in results if r is True)

    def get_project_connection_count(self, project_id: str) -> int:
        return len(self._project_index.get(project_id, set()))

    def get_total_connections(self) -> int:
        return len(self._connections)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_connections": len(self._connections),
            "active_projects": len(self._project_index),
            "active_users": len(self._user_index),
            "connections_per_project": {
                pid: len(cids) for pid, cids in self._project_index.items()
            },
        }


manager = ConnectionManager()