"""
ResearchOS — Dependency Injection

FastAPI dependency functions for database sessions, Redis clients,
configuration access, and authentication.
"""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.database import get_async_session
from app.integrations.redis_client import RedisManager
from app.core.security import CurrentUser, get_current_user  # noqa: F401


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_async_session() as session:
        yield session


async def get_redis() -> RedisManager:
    """
    Get the Redis manager singleton.

    Usage:
        @router.get("/cached")
        async def get_cached(redis: RedisManager = Depends(get_redis)):
            ...
    """
    return RedisManager()


def get_current_settings() -> Settings:
    """
    Get application settings singleton.

    Usage:
        @router.get("/config")
        async def get_config(settings: Settings = Depends(get_current_settings)):
            ...
    """
    return get_settings()
