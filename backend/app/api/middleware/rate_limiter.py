"""Redis-backed sliding-window rate limiter middleware.

If Redis is unavailable, falls back to an in-memory ``dict`` so the
application never crashes due to a missing cache layer.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, Optional

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import Settings

logger = structlog.stdlib.get_logger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiter.

    Uses Redis ``ZRANGEBYSCORE`` / ``ZADD`` for distributed deployments.
    When Redis is ``None`` an in-memory fallback is used (single-process
    only, suitable for development).

    Args:
        app: The ASGI application.
        settings: Application settings (``rate_limit_per_minute``).
        redis_client: An ``redis.asyncio.Redis`` instance or ``None``.
    """

    def __init__(
        self,
        app: Any,
        settings: Settings,
        redis_client: Any | None = None,
    ) -> None:
        super().__init__(app)
        self._limit = settings.rate_limit_per_minute
        self._window = 60  # seconds
        self._redis = redis_client
        # Fallback: {ip: [timestamp, …]}
        self._memory_store: Dict[str, list[float]] = defaultdict(list)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _client_ip(self, request: Request) -> str:
        """Extract the client IP from the request, respecting proxies."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    async def _check_redis(self, key: str, now: float) -> tuple[bool, int]:
        """Perform rate-limit check via Redis sorted set.

        Returns:
            Tuple of (is_allowed, current_count).
        """
        assert self._redis is not None
        window_start = now - self._window

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, self._window + 1)
        results = await pipe.execute()
        count: int = results[2]

        if count > self._limit:
            # Remove the entry we just added since request is rejected
            await self._redis.zrem(key, str(now))
            return False, count - 1

        return True, count

    def _check_memory(self, ip: str, now: float) -> tuple[bool, int]:
        """Fallback in-memory sliding window check.

        Returns:
            Tuple of (is_allowed, current_count).
        """
        window_start = now - self._window
        # Prune expired timestamps
        self._memory_store[ip] = [
            ts for ts in self._memory_store[ip] if ts > window_start
        ]
        count = len(self._memory_store[ip])

        if count >= self._limit:
            return False, count

        self._memory_store[ip].append(now)
        return True, count + 1

    # ── Middleware entry point ────────────────────────────────────────────

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Check rate limit before forwarding the request."""
        # Skip rate limiting for health-check and docs
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.time()
        key = f"researchos:ratelimit:{ip}"

        allowed: bool
        count: int

        if self._redis is not None:
            try:
                allowed, count = await self._check_redis(key, now)
            except Exception:
                logger.warning(
                    "rate_limiter.redis_error",
                    ip=ip,
                    exc_info=True,
                )
                # Degrade to memory
                allowed, count = self._check_memory(ip, now)
        else:
            allowed, count = self._check_memory(ip, now)

        remaining = max(0, self._limit - count)
        reset_at = int(now) + self._window

        if not allowed:
            logger.warning("rate_limiter.exceeded", ip=ip, count=count)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitError",
                    "detail": "Rate limit exceeded. Please try again later.",
                },
                headers={
                    "X-RateLimit-Limit": str(self._limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                    "Retry-After": str(self._window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response
