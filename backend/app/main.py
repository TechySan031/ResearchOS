"""
ResearchOS — FastAPI Application Factory

Production-grade app factory with lifespan management, middleware stack,
and router aggregation.
"""

from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse
from app.integrations.pinecone_client import PineconeManager
from app.config import get_settings, validate_production_settings
from app.utils.logging import configure_logging, get_logger
from app.utils.metrics import setup_metrics
from app.models.database import async_session_factory, init_db
from app.integrations.redis_client import RedisManager
from app.api.middleware.cors import add_cors_middleware
from app.api.middleware.rate_limiter import RateLimiterMiddleware
from app.api.middleware.request_logging import RequestLoggingMiddleware
from app.api.middleware.error_handler import add_exception_handlers


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — startup and shutdown hooks."""
    settings = get_settings()
    configure_logging()

    # Fail fast if production config is invalid
    validate_production_settings()

    logger.info(
        "starting_application",
        app_name=settings.app_name,
        env=settings.app_env,
        debug=settings.app_debug,
    )

    # ---- Startup ----
    # Initialize database tables
    await init_db()
    logger.info("database_initialized")
    # Initialize Pinecone
    try:
        pinecone = PineconeManager()
        await pinecone.init_index()
        logger.info("pinecone_initialized")
    except Exception as e:
        logger.error(
            "pinecone_init_failed",
            error=str(e)
        )

    redis_manager = RedisManager()
    await redis_manager.connect()

    # Setup Prometheus metrics
    setup_metrics()
    logger.info("metrics_initialized")

    logger.info(
        "application_ready",
        host=settings.app_host,
        port=settings.app_port,
        docs_url="/docs",
    )

    yield

    # ---- Shutdown ----
    logger.info("shutting_down_application")
    await redis_manager.disconnect()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """
    FastAPI application factory.

    Creates and configures the FastAPI app with all middleware,
    routers, and lifecycle hooks.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "AI Research Operating System — Multi-agent research workflow "
            "automation platform with RAG pipelines, citation grounding, "
            "and publication assistance."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ---- Middleware Stack (order matters — outermost first) ----
    # Request logging (outermost — captures full request lifecycle)
    app.add_middleware(RequestLoggingMiddleware)

    # Rate limiting
    app.add_middleware(
        RateLimiterMiddleware,
        settings=settings,
    )

    # CORS
    add_cors_middleware(app, settings)

    # Error handlers
    add_exception_handlers(app)

    # ---- Routers ----
    from app.api.v1.router import v1_router

    app.include_router(v1_router, prefix="/api/v1")

    # ---- Root Endpoints ----
    @app.get("/", tags=["Root"])
    async def root():
        """API root — returns service info."""
        return {
            "service": settings.app_name,
            "version": "0.1.0",
            "description": "AI Research Operating System",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1",
        }

    # ---- Startup time for uptime tracking ----
    import time as _time

    _startup_ts = _time.time()

    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Production health check endpoint.

        Returns comprehensive service health including dependency
        connectivity. Returns 503 if critical dependencies are down.
        """
        checks: dict[str, str] = {}
        is_healthy = True

        # ── Database ──
        try:
            # pyrefly: ignore [missing-import]
            from sqlalchemy import text as sa_text

            async with async_session_factory() as session:
                await session.execute(sa_text("SELECT 1"))
            checks["database"] = "connected"
        except Exception as exc:
            checks["database"] = f"error: {type(exc).__name__}"
            is_healthy = False

        # ── Redis ──
        try:
            redis = RedisManager()
            if redis._client:
                await redis._client.ping()
                checks["redis"] = "connected"
            else:
                checks["redis"] = "not_configured"
        except Exception:
            checks["redis"] = "disconnected"
            # Redis is non-critical — don't mark unhealthy

        # ── Pinecone ──
        try:
            from app.integrations.pinecone_client import PineconeManager
            if settings.pinecone_api_key:
                pm = PineconeManager()
                await pm.init_index()
                stats = await pm.get_index_stats()
                checks["pinecone"] = f"connected (vectors: {stats.get('total_vector_count', 0)})"
            else:
                checks["pinecone"] = "not_configured"
        except Exception as exc:
            checks["pinecone"] = f"error: {type(exc).__name__}"
            # Pinecone is non-critical — don't mark unhealthy

        # ── Uptime ──
        uptime_secs = round(_time.time() - _startup_ts, 1)

        status_code = 200 if is_healthy else 503
        status_label = "healthy" if is_healthy else "unhealthy"

        health = {
            "status": status_label,
            "service": settings.app_name,
            "version": "0.1.0",
            "environment": settings.app_env,
            "uptime_seconds": uptime_secs,
            "checks": checks,
        }

        return JSONResponse(content=health, status_code=status_code)

    return app


# Application instance (used by uvicorn)
app = create_app()
