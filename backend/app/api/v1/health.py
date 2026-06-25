"""Health check API endpoints.

Provides ``/health``, ``/health/live``, ``/health/ready``,
``/health/database``, and ``/health/redis`` endpoints for Kubernetes
probes and operational monitoring.
"""

from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.database import async_session_factory
from app.integrations.redis_client import RedisManager
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])

_startup_ts: float = time.time()


@router.get("", summary="Comprehensive health check")
async def health_check():
    """Production health check — returns overall service health with
    dependency connectivity status."""
    settings = get_settings()
    checks: dict[str, str] = {}
    is_healthy = True

    # Database
    try:
        from sqlalchemy import text as sa_text

        async with async_session_factory() as session:
            await session.execute(sa_text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
        is_healthy = False

    # Redis
    try:
        redis = RedisManager()
        if redis._client:
            await redis._client.ping()
            checks["redis"] = "connected"
        else:
            checks["redis"] = "not_configured"
    except Exception:
        checks["redis"] = "disconnected"

    uptime_secs = round(time.time() - _startup_ts, 1)
    status_code = 200 if is_healthy else 503
    status_label = "healthy" if is_healthy else "unhealthy"

    return JSONResponse(
        content={
            "status": status_label,
            "service": settings.app_name,
            "version": "0.1.0",
            "environment": settings.app_env,
            "uptime_seconds": uptime_secs,
            "checks": checks,
        },
        status_code=status_code,
    )


@router.get("/live", summary="Liveness probe")
async def liveness():
    """Kubernetes liveness probe — always returns 200 if the process is
    running."""
    return {"status": "alive"}


@router.get("/ready", summary="Readiness probe")
async def readiness():
    """Kubernetes readiness probe — returns 200 when the database is
    reachable, 503 otherwise."""
    try:
        from sqlalchemy import text as sa_text

        async with async_session_factory() as session:
            await session.execute(sa_text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        return JSONResponse(
            content={"status": "not_ready", "error": type(exc).__name__},
            status_code=503,
        )


@router.get("/database", summary="Database health")
async def database_health():
    """Check database connectivity."""
    try:
        from sqlalchemy import text as sa_text

        async with async_session_factory() as session:
            await session.execute(sa_text("SELECT 1"))
        return {"status": "connected"}
    except Exception as exc:
        return JSONResponse(
            content={"status": "error", "error": str(exc)},
            status_code=503,
        )


@router.get("/redis", summary="Redis health")
async def redis_health():
    """Check Redis connectivity."""
    try:
        redis = RedisManager()
        if redis._client:
            await redis._client.ping()
            return {"status": "connected"}
        return {"status": "not_configured"}
    except Exception as exc:
        return JSONResponse(
            content={"status": "disconnected", "error": str(exc)},
            status_code=503,
        )
