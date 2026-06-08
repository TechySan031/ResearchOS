"""Tests for configuration module."""

import pytest

from app.config import Settings, get_settings


class TestSettings:
    """Test Pydantic Settings configuration."""

    def test_settings_singleton(self):
        """get_settings() returns the same object on repeated calls."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_default_app_name(self):
        settings = get_settings()
        assert settings.app_name == "ResearchOS"

    def test_default_environment(self):
        settings = get_settings()
        assert settings.app_env in ("development", "testing", "production")

    def test_default_port(self):
        settings = get_settings()
        assert settings.app_port == 8000

    def test_default_database_url(self):
        settings = get_settings()
        assert "sqlite" in settings.database_url or "postgresql" in settings.database_url

    def test_embedding_model(self):
        settings = get_settings()
        assert "bge" in settings.embedding_model.lower() or "BAAI" in settings.embedding_model

    def test_embedding_dimension(self):
        settings = get_settings()
        assert settings.embedding_dimension == 1024

    def test_cors_origins_is_list(self):
        settings = get_settings()
        assert isinstance(settings.cors_origins, list)

    def test_is_production_false_by_default(self):
        settings = get_settings()
        assert settings.is_production is False

    def test_is_development_true_by_default(self):
        settings = get_settings()
        assert settings.is_development is True


class TestSettingsValidators:
    """Test field validators."""

    def test_parse_cors_origins_from_json_string(self):
        parsed = Settings.parse_cors_origins('["http://localhost:3000"]')
        assert parsed == ["http://localhost:3000"]

    def test_parse_cors_origins_from_list(self):
        parsed = Settings.parse_cors_origins(["http://localhost"])
        assert parsed == ["http://localhost"]

    def test_parse_cors_origins_single_string(self):
        parsed = Settings.parse_cors_origins("http://localhost:3000")
        assert parsed == ["http://localhost:3000"]

    def test_normalize_log_level_uppercased(self):
        result = Settings.normalize_log_level("debug")
        assert result == "DEBUG"

    def test_normalize_log_level_already_upper(self):
        result = Settings.normalize_log_level("INFO")
        assert result == "INFO"
