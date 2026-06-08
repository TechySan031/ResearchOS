"""Tests for agent node base utilities."""

import pytest
from datetime import datetime

from app.agents.nodes.base import (
    make_history_entry,
    make_error_entry,
    _papers_context,
)


class TestMakeHistoryEntry:
    """Test history entry creation."""

    def test_basic_entry(self):
        entry = make_history_entry("test_agent")
        assert entry["agent"] == "test_agent"
        assert entry["status"] == "completed"
        assert "timestamp" in entry

    def test_custom_status(self):
        entry = make_history_entry("agent", "failed")
        assert entry["status"] == "failed"

    def test_extra_fields(self):
        entry = make_history_entry("agent", elapsed=5.2, count=10)
        assert entry["elapsed"] == 5.2
        assert entry["count"] == 10

    def test_timestamp_is_iso_format(self):
        entry = make_history_entry("agent")
        # Should parse without error
        datetime.fromisoformat(entry["timestamp"])


class TestMakeErrorEntry:
    """Test error entry creation."""

    def test_basic_error(self):
        entry = make_error_entry("test_agent", "Something broke")
        assert entry["agent"] == "test_agent"
        assert entry["error"] == "Something broke"
        assert "timestamp" in entry


class TestPapersContext:
    """Test paper context formatting for LLM prompts."""

    def test_formats_papers(self):
        papers = [
            {
                "title": "Test Paper",
                "authors": ["Alice", "Bob"],
                "abstract": "This is a test abstract.",
                "year": 2024,
                "doi": "10.1234/test",
                "source": "arxiv",
            }
        ]
        context = _papers_context(papers)
        assert "[REF_1]" in context
        assert "Test Paper" in context
        assert "Alice" in context
        assert "2024" in context
        assert "10.1234/test" in context

    def test_limits_papers(self):
        papers = [{"title": f"Paper {i}", "authors": [], "abstract": ""} for i in range(50)]
        context = _papers_context(papers, max_papers=5)
        assert "[REF_5]" in context
        assert "[REF_6]" not in context

    def test_truncates_long_authors(self):
        papers = [
            {
                "title": "Many Authors",
                "authors": ["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
                "abstract": "",
            }
        ]
        context = _papers_context(papers)
        assert "et al." in context

    def test_empty_papers(self):
        assert _papers_context([]) == ""

    def test_handles_missing_fields(self):
        papers = [{"title": "Minimal Paper"}]
        context = _papers_context(papers)
        assert "Minimal Paper" in context
        assert "N/A" in context or "No abstract" in context
