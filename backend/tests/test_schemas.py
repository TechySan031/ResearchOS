"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    PaperSearchRequest,
    ResearchStartRequest,
    ResearchStatusResponse,
    PaginatedResponse,
    WebSocketMessage,
    HealthResponse,
    ExportRequest,
)


class TestProjectCreate:
    """Tests for ProjectCreate schema."""

    def test_valid_creation(self):
        data = ProjectCreate(title="Test Project")
        assert data.title == "Test Project"

    def test_title_required(self):
        with pytest.raises(ValidationError):
            ProjectCreate()

    def test_title_min_length(self):
        with pytest.raises(ValidationError):
            ProjectCreate(title="")

    def test_optional_fields(self):
        data = ProjectCreate(title="Test", description="Desc", topic="AI")
        assert data.description == "Desc"
        assert data.topic == "AI"

    def test_settings_dict(self):
        data = ProjectCreate(title="Test", settings={"format": "ieee"})
        assert data.settings["format"] == "ieee"


class TestProjectUpdate:
    """Tests for ProjectUpdate schema."""

    def test_all_fields_optional(self):
        data = ProjectUpdate()
        assert data.title is None
        assert data.description is None

    def test_partial_update(self):
        data = ProjectUpdate(title="New Title")
        assert data.title == "New Title"
        assert data.description is None

    def test_exclude_unset(self):
        data = ProjectUpdate(title="New Title")
        dumped = data.model_dump(exclude_unset=True)
        assert "title" in dumped
        assert "description" not in dumped


class TestPaperSearchRequest:
    """Tests for PaperSearchRequest schema."""

    def test_valid_search(self):
        req = PaperSearchRequest(query="transformer attention")
        assert req.query == "transformer attention"
        assert req.max_results == 10  # default

    def test_query_required(self):
        with pytest.raises(ValidationError):
            PaperSearchRequest()

    def test_max_results_range(self):
        req = PaperSearchRequest(query="test", max_results=50)
        assert req.max_results == 50

    def test_max_results_too_high(self):
        with pytest.raises(ValidationError):
            PaperSearchRequest(query="test", max_results=200)

    def test_max_results_too_low(self):
        with pytest.raises(ValidationError):
            PaperSearchRequest(query="test", max_results=0)


class TestResearchStartRequest:
    """Tests for ResearchStartRequest schema."""

    def test_valid_request(self):
        req = ResearchStartRequest(project_id="test-123")
        assert req.max_papers == 20
        assert req.format_style == "ieee"

    def test_format_style_validation(self):
        req = ResearchStartRequest(project_id="test", format_style="acm")
        assert req.format_style == "acm"

    def test_invalid_format_style(self):
        with pytest.raises(ValidationError):
            ResearchStartRequest(project_id="test", format_style="invalid")


class TestResearchStatusResponse:
    """Tests for ResearchStatusResponse schema."""

    def test_minimal_response(self):
        resp = ResearchStatusResponse(project_id="p1", status="running")
        assert resp.progress_pct == 0.0
        assert resp.current_agent is None

    def test_progress_bounds(self):
        with pytest.raises(ValidationError):
            ResearchStatusResponse(project_id="p1", status="x", progress_pct=150)


class TestExportRequest:
    """Tests for ExportRequest schema."""

    def test_default_format(self):
        req = ExportRequest(project_id="p1")
        assert req.format == "pdf"

    def test_valid_formats(self):
        for fmt in ["pdf", "docx", "markdown", "latex"]:
            req = ExportRequest(project_id="p1", format=fmt)
            assert req.format == fmt

    def test_invalid_format(self):
        with pytest.raises(ValidationError):
            ExportRequest(project_id="p1", format="html")


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_defaults(self):
        resp = HealthResponse(version="0.1.0", environment="dev")
        assert resp.status == "ok"
        assert resp.database == "connected"
        assert resp.redis == "connected"


class TestWebSocketMessage:
    """Tests for WebSocketMessage schema."""

    def test_minimal_message(self):
        msg = WebSocketMessage(type="ping")
        assert msg.type == "ping"
        assert msg.data == {}

    def test_with_data(self):
        msg = WebSocketMessage(type="agent_event", data={"score": 0.8})
        assert msg.data["score"] == 0.8
