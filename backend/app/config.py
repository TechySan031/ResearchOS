"""Application configuration loaded from environment variables and .env files.

Uses pydantic-settings ``BaseSettings`` so that every value can be overridden by
a real environment variable, a ``.env`` file, or a Secret-Manager mount.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the ResearchOS backend.

    Reads from a ``.env`` file located one level above the ``app/`` package
    (i.e. ``backend/.env``) and falls back to sensible development defaults.
    """

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "ResearchOS"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "DEBUG"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./researchos.db"

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── LLM Providers ────────────────────────────────────────────────────
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"

    kimi_api_key: str = ""
    kimi_model: str = "moonshot-v1-128k"
    kimi_base_url: str = "https://api.moonshot.cn/v1"

    # ── Pinecone ─────────────────────────────────────────────────────────
    pinecone_api_key: str = ""
    pinecone_index_name: str = "research-os"
    pinecone_environment: str = "us-east-1"

    # ── Embeddings ───────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dimension: int = 1024
    embedding_device: str = "cpu"

    # ── External Research APIs ───────────────────────────────────────────
    semantic_scholar_api_key: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── JWT Auth ───────────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    jwt_refresh_expiration_days: int = 7

    # ── Per-Endpoint Rate Limits (requests per minute) ────────────────────
    rate_limit_auth_per_minute: int = 20
    rate_limit_workflow_per_minute: int = 10
    rate_limit_copilot_per_minute: int = 30
    rate_limit_project_create_per_minute: int = 10

    # ── Security ─────────────────────────────────────────────────────────
    max_request_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | List[str]) -> List[str]:
        """Accept both JSON-encoded strings and plain Python lists."""
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(o) for o in parsed]
            except (json.JSONDecodeError, TypeError):
                # Treat as a single origin
                return [value]
        return value  # type: ignore[return-value]

    @field_validator("app_log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Uppercase the log level for consistency."""
        return value.upper() if isinstance(value, str) else value

    # ── Derived helpers ──────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        """Return ``True`` when running in a production environment."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Return ``True`` when running in a development environment."""
        return self.app_env.lower() == "development"

    @property
    def is_testing(self) -> bool:
        """Return ``True`` when running under the test harness."""
        return self.app_env.lower() == "testing"

    def validate_production(self) -> list[str]:
        """Validate settings for production readiness.

        Returns a list of warning/error messages.  An empty list means
        all production checks pass.
        """
        errors: list[str] = []

        if "sqlite" in self.database_url.lower():
            errors.append(
                "DATABASE_URL uses SQLite — use PostgreSQL for production"
            )

        if self.jwt_secret_key == "change-me-in-production":
            errors.append(
                "JWT_SECRET_KEY is still the default — set a secure secret"
            )

        if self.app_debug:
            errors.append("APP_DEBUG is True — must be False in production")

        if self.app_log_level == "DEBUG":
            errors.append(
                "APP_LOG_LEVEL is DEBUG — use INFO or WARNING in production"
            )

        if not self.mistral_api_key:
            errors.append("MISTRAL_API_KEY is not set")

        if not self.pinecone_api_key:
            errors.append("PINECONE_API_KEY is not set")

        return errors


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application settings singleton.

    The result is cached so that subsequent calls return the same object
    without re-reading environment variables.
    """
    return Settings()  # type: ignore[call-arg]


def validate_production_settings() -> None:
    """Check production readiness and log warnings.

    Called during application startup when ``APP_ENV=production``.
    Raises ``SystemExit`` if critical checks fail.
    """
    s = get_settings()
    if not s.is_production:
        return

    errors = s.validate_production()
    if not errors:
        return

    import logging

    logger = logging.getLogger("researchos.config")
    critical = [e for e in errors if "SQLite" in e or "JWT_SECRET" in e]
    warnings = [e for e in errors if e not in critical]

    for w in warnings:
        logger.warning("Production config warning: %s", w)

    if critical:
        for c in critical:
            logger.critical("Production config CRITICAL: %s", c)
        raise SystemExit(
            f"Cannot start in production mode: {len(critical)} critical "
            f"configuration error(s). See logs above."
        )


# Module-level convenience alias
settings: Settings = get_settings()

