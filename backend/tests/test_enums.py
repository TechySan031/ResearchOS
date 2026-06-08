"""Tests for the enums module."""

import pytest

from app.models.enums import (
    WorkflowStatus,
    AgentName,
    PaperSource,
    CitationStatus,
    FormatStyle,
    AgentEventType,
)


class TestWorkflowStatus:
    """Test WorkflowStatus enum values."""

    def test_all_statuses_exist(self):
        expected = {"created", "researching", "drafting", "reviewing",
                    "completed", "failed", "paused"}
        actual = {s.value for s in WorkflowStatus}
        assert expected.issubset(actual)

    def test_string_value(self):
        assert WorkflowStatus.CREATED.value == "created"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"


class TestAgentName:
    """Test AgentName enum covers all 11+ agents."""

    def test_has_all_agents(self):
        names = {a.value for a in AgentName}
        expected_agents = {
            "planner",
            "researcher",
            "writer",
        }
        # At minimum, these must exist
        assert expected_agents.issubset(names)

    def test_agent_count(self):
        """There should be at least 11 agents."""
        assert len(AgentName) >= 11


class TestPaperSource:
    """Test PaperSource enum."""

    def test_has_required_sources(self):
        sources = {s.value for s in PaperSource}
        assert "arxiv" in sources
        assert "semantic_scholar" in sources
        assert "crossref" in sources
        assert "upload" in sources


class TestCitationStatus:
    """Test CitationStatus enum."""

    def test_has_required_statuses(self):
        statuses = {s.value for s in CitationStatus}
        assert "verified" in statuses
        assert "unverified" in statuses
        assert "failed" in statuses


class TestFormatStyle:
    """Test FormatStyle enum."""

    def test_has_required_styles(self):
        styles = {s.value for s in FormatStyle}
        assert "ieee" in styles
        assert "acm" in styles
        assert "springer" in styles


class TestAgentEventType:
    """Test AgentEventType enum."""

    def test_has_lifecycle_events(self):
        events = {e.value for e in AgentEventType}
        assert "started" in events
        assert "completed" in events
        assert "failed" in events
