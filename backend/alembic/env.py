"""Alembic environment configuration for ResearchOS (async engine).

Supports:
- Async engines (SQLite+aiosqlite for dev, PostgreSQL+asyncpg for prod)
- Offline (--sql) mode with dialect-appropriate sync URLs
- Online mode via ``run_async_migrations()`` pattern
"""
import asyncio
import os
import sys
from logging.config import fileConfig

# Add backend directory to Python path BEFORE importing app.*
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.models.database import Base
# ── Alembic Config object ───────────────────────────────────────────────────

config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for 'autogenerate' support
target_metadata = Base.metadata

# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_database_url() -> str:
    """Return the database URL from application settings."""
    return get_settings().database_url


def _make_sync_url(url: str) -> str:
    """Convert an async driver URL to its synchronous equivalent.

    Alembic's *offline* mode renders raw SQL and needs a sync dialect string.
    The online mode uses ``async_engine_from_config`` which handles async
    drivers natively.
    """
    replacements = {
        "sqlite+aiosqlite": "sqlite",
        "postgresql+asyncpg": "postgresql",
        "mysql+aiomysql": "mysql+pymysql",
    }
    for async_prefix, sync_prefix in replacements.items():
        if url.startswith(async_prefix):
            return url.replace(async_prefix, sync_prefix, 1)
    return url


# ── Offline (--sql) migrations ───────────────────────────────────────────────


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This emits the SQL statements to stdout without requiring a live
    database connection.  We convert the async URL to a sync dialect so
    that Alembic can resolve the correct DDL compiler.
    """
    url = _make_sync_url(_get_database_url())
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite requires batch mode for ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online (live DB) migrations ──────────────────────────────────────────────


def do_run_migrations(connection: Connection) -> None:
    """Configure the Alembic context with a real connection and run."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # SQLite requires batch mode for ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside a connection."""
    # Override alembic.ini's sqlalchemy.url with the live settings value.
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine support."""
    asyncio.run(run_async_migrations())


# ── Entrypoint ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
