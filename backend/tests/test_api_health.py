"""Tests for API health check and root endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import create_app


@pytest_asyncio.fixture
async def client(monkeypatch):
    """Lightweight async client with mocked DB connectivity for health check."""
    from unittest.mock import MagicMock, AsyncMock
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    
    monkeypatch.setattr("app.main.async_session_factory", mock_session_factory)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestRootEndpoint:
    """Test the / root endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_service_info(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "ResearchOS"
        assert "version" in data
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"

    @pytest.mark.asyncio
    async def test_root_has_api_prefix(self, client):
        resp = await client.get("/")
        data = resp.json()
        assert data["api"] == "/api/v1"


class TestHealthEndpoint:
    """Test the /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_structure(self, client):
        resp = await client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
        assert "environment" in data
        assert "uptime_seconds" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
        assert "pinecone" in data["checks"]


class TestOpenAPI:
    """Test that OpenAPI docs are accessible."""

    @pytest.mark.asyncio
    async def test_openapi_json(self, client):
        resp = await client.get("/api/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert "paths" in data
        assert data["info"]["title"] == "ResearchOS"

    @pytest.mark.asyncio
    async def test_docs_page(self, client):
        resp = await client.get("/docs")
        assert resp.status_code == 200
