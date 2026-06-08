"""Tests for the research retrieval node helpers.

Tests pure utility functions (query generation, dedup, ranking)
without requiring real API calls.
"""

import pytest

from app.agents.nodes.research_retrieval import (
    _generate_queries,
    _deduplicate_papers,
    _rank_papers,
    _normalise_title,
    _title_hash,
)


class TestGenerateQueries:
    """Test search query generation from topic."""

    def test_generates_multiple_queries(self):
        queries = _generate_queries("transformer attention mechanisms")
        assert len(queries) >= 3
        assert len(queries) <= 5

    def test_includes_original_topic(self):
        topic = "protein folding with deep learning"
        queries = _generate_queries(topic)
        assert topic in queries

    def test_includes_survey_variant(self):
        queries = _generate_queries("graph neural networks")
        assert any("survey" in q.lower() or "review" in q.lower() for q in queries)

    def test_includes_recent_advances(self):
        queries = _generate_queries("CRISPR gene editing")
        assert any("recent" in q.lower() for q in queries)

    def test_no_duplicates(self):
        queries = _generate_queries("test topic")
        normalized = [q.lower().strip() for q in queries]
        assert len(normalized) == len(set(normalized))

    def test_empty_topic(self):
        queries = _generate_queries("")
        assert len(queries) >= 1


class TestDeduplicatePapers:
    """Test paper deduplication logic."""

    def test_dedup_by_doi(self):
        papers = [
            {"title": "Paper A", "doi": "10.1234/a"},
            {"title": "Paper A Copy", "doi": "10.1234/a"},
            {"title": "Paper B", "doi": "10.1234/b"},
        ]
        result = _deduplicate_papers(papers)
        assert len(result) == 2

    def test_dedup_by_title(self):
        papers = [
            {"title": "Exact Same Title", "doi": ""},
            {"title": "Exact Same Title", "doi": ""},
            {"title": "Different Title", "doi": ""},
        ]
        result = _deduplicate_papers(papers)
        assert len(result) == 2

    def test_preserves_unique_papers(self):
        papers = [
            {"title": "Unique A", "doi": "10.1/a"},
            {"title": "Unique B", "doi": "10.1/b"},
            {"title": "Unique C", "doi": "10.1/c"},
        ]
        result = _deduplicate_papers(papers)
        assert len(result) == 3

    def test_empty_list(self):
        assert _deduplicate_papers([]) == []

    def test_single_paper(self):
        papers = [{"title": "Solo", "doi": "10.1/solo"}]
        assert len(_deduplicate_papers(papers)) == 1


class TestRankPapers:
    """Test paper ranking by citation count and year."""

    def test_ranks_by_citation_count(self):
        papers = [
            {"title": "Low", "citation_count": 5, "year": 2024},
            {"title": "High", "citation_count": 100, "year": 2024},
            {"title": "Mid", "citation_count": 30, "year": 2024},
        ]
        ranked = _rank_papers(papers)
        assert ranked[0]["title"] == "High"
        assert ranked[1]["title"] == "Mid"
        assert ranked[2]["title"] == "Low"

    def test_breaks_ties_by_year(self):
        papers = [
            {"title": "Old", "citation_count": 50, "year": 2020},
            {"title": "New", "citation_count": 50, "year": 2024},
        ]
        ranked = _rank_papers(papers)
        assert ranked[0]["title"] == "New"

    def test_handles_missing_citation_count(self):
        papers = [
            {"title": "No count", "year": 2024},
            {"title": "Has count", "citation_count": 10, "year": 2024},
        ]
        ranked = _rank_papers(papers)
        assert ranked[0]["title"] == "Has count"

    def test_empty_list(self):
        assert _rank_papers([]) == []


class TestNormaliseTitleAndHash:
    """Test title normalization and hashing."""

    def test_normalises_case(self):
        assert _normalise_title("Hello World") == _normalise_title("hello world")

    def test_removes_stop_words(self):
        result = _normalise_title("The Impact of AI on Healthcare")
        assert "the" not in result
        assert "of" not in result
        assert "on" not in result

    def test_removes_punctuation(self):
        result = _normalise_title("Hello, World!")
        assert "," not in result
        assert "!" not in result

    def test_same_title_same_hash(self):
        h1 = _title_hash("Attention Is All You Need")
        h2 = _title_hash("attention is all you need")
        assert h1 == h2

    def test_different_titles_different_hash(self):
        h1 = _title_hash("Paper A about topic X")
        h2 = _title_hash("Paper B about topic Y")
        assert h1 != h2
