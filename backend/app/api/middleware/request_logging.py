"""Request / response logging middleware with correlation IDs.

Every incoming request is assigned a unique ``X-Correlation-ID`` (or reuses
the one provided by the caller) so that log entries can be correlated across
service boundaries.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import CORRELATION_ID_HEADER

logger = structlog.stdlib.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status, and duration.

    Also injects a ``correlation_id`` into the structlog context so that
    all downstream log entries carry the same trace identifier.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Wrap the request lifecycle with timing and structured logging."""
        correlation_id = request.headers.get(
            CORRELATION_ID_HEADER,
            str(uuid.uuid4()),
        )

        # Bind correlation_id into structlog context vars for downstream use
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        logger.info(
            "http.request.start",
            method=method,
            path=path,
            client=self._client_ip(request),
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "http.request.unhandled_error",
                method=method,
                path=path,
                duration_ms=duration_ms,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http.request.end",
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # Propagate correlation_id to the client
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"
