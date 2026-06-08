"""Tests for the retrieval verification module.

Pure logic tests — no external services, no mocking needed.
"""

import pytest

from app.rag.verification import RetrievalVerifier, VerificationReport


def _make_result(score=0.8, paper_id="p1", section="intro", year=2024):
    """Create a mock retrieval result dict."""
    return {
        "score": score,
        "paper_id": paper_id,
        "section": section,
        "metadata": {"year": year},
    }


class TestRetrievalVerifier:
    """Test retrieval quality verification logic."""

    @pytest.fixture
    def verifier(self):
        return RetrievalVerifier()

    @pytest.mark.asyncio
    async def test_empty_results(self, verifier):
        report = await verifier.verify_retrieval_quality("test query", [])
        assert report.quality_grade == "F"
        assert report.total_results == 0
        assert not report.is_acceptable()
        assert len(report.warnings) > 0

    @pytest.mark.asyncio
    async def test_high_quality_results(self, verifier):
        results = [
            _make_result(0.9, "p1", "intro", 2024),
            _make_result(0.85, "p2", "methods", 2023),
            _make_result(0.8, "p3", "results", 2022),
            _make_result(0.75, "p4", "discussion", 2024),
            _make_result(0.7, "p5", "abstract", 2023),
        ]
        report = await verifier.verify_retrieval_quality("test", results, current_year=2024)

        assert report.avg_relevance_score >= 0.7
        assert report.diversity_score == 1.0  # All unique papers
        assert report.total_results == 5
        assert report.unique_papers == 5
        assert report.quality_grade in ("A", "B")
        assert report.is_acceptable()

    @pytest.mark.asyncio
    async def test_low_relevance_warning(self, verifier):
        results = [
            _make_result(0.3, "p1"),
            _make_result(0.2, "p2"),
            _make_result(0.1, "p3"),
        ]
        report = await verifier.verify_retrieval_quality("test", results)
        assert report.avg_relevance_score < 0.5
        assert any("relevance" in w.lower() for w in report.warnings)

    @pytest.mark.asyncio
    async def test_low_diversity_warning(self, verifier):
        """All results from the same paper should produce low diversity score."""
        results = [
            _make_result(0.9, "p1", "intro"),
            _make_result(0.85, "p1", "methods"),
            _make_result(0.8, "p1", "results"),
        ]
        report = await verifier.verify_retrieval_quality("test", results)
        assert report.diversity_score < 0.5
        assert report.unique_papers == 1

    @pytest.mark.asyncio
    async def test_recency_scoring(self, verifier):
        """Old papers should score low on recency."""
        results = [
            _make_result(0.9, "p1", "intro", 2010),
            _make_result(0.85, "p2", "methods", 2012),
            _make_result(0.8, "p3", "results", 2008),
        ]
        report = await verifier.verify_retrieval_quality("test", results, current_year=2024)
        assert report.recency_score == 0.0  # All older than 5 years
        assert report.year_range == (2008, 2012)

    @pytest.mark.asyncio
    async def test_mixed_recency(self, verifier):
        results = [
            _make_result(0.9, "p1", "intro", 2024),
            _make_result(0.85, "p2", "methods", 2010),
        ]
        report = await verifier.verify_retrieval_quality("test", results, current_year=2024)
        assert report.recency_score == 0.5  # 1 of 2 recent

    @pytest.mark.asyncio
    async def test_few_results_warning(self, verifier):
        results = [_make_result(0.9, "p1")]
        report = await verifier.verify_retrieval_quality("test", results)
        assert any("only" in w.lower() for w in report.warnings)

    @pytest.mark.asyncio
    async def test_quality_grade_computation(self, verifier):
        """Test that composite scoring maps to correct grades."""
        # Perfect results
        perfect = [_make_result(1.0, f"p{i}", "intro", 2024) for i in range(10)]
        report = await verifier.verify_retrieval_quality("test", perfect, current_year=2024)
        assert report.quality_grade == "A"

    @pytest.mark.asyncio
    async def test_is_acceptable_threshold(self, verifier):
        results = [
            _make_result(0.6, "p1"),
            _make_result(0.55, "p2"),
            _make_result(0.5, "p3"),
        ]
        report = await verifier.verify_retrieval_quality("test", results)
        assert report.is_acceptable()  # Meets all minimum thresholds

    @pytest.mark.asyncio
    async def test_dict_and_object_results(self, verifier):
        """Verify both dict and dataclass results are handled."""

        class MockResult:
            def __init__(self):
                self.score = 0.9
                self.paper_id = "p1"
                self.section = "intro"
                self.metadata = {"year": 2024}

        results = [MockResult(), MockResult()]
        report = await verifier.verify_retrieval_quality("test", results, current_year=2024)
        assert report.total_results == 2

    @pytest.mark.asyncio
    async def test_missing_year_metadata(self, verifier):
        """Results without year metadata should not crash."""
        results = [
            {"score": 0.9, "paper_id": "p1", "section": "intro", "metadata": {}},
            {"score": 0.8, "paper_id": "p2", "section": "methods"},
        ]
        report = await verifier.verify_retrieval_quality("test", results)
        assert report.recency_score == 0.0  # No years available


class TestVerificationReport:
    """Test VerificationReport dataclass."""

    def test_is_acceptable_all_pass(self):
        report = VerificationReport(
            avg_relevance_score=0.8,
            diversity_score=0.5,
            recency_score=0.7,
            total_sources=5,
            total_results=5,
            unique_papers=5,
            unique_sections=3,
        )
        assert report.is_acceptable()

    def test_is_acceptable_fails_relevance(self):
        report = VerificationReport(
            avg_relevance_score=0.3,
            diversity_score=0.5,
            recency_score=0.7,
            total_sources=5,
            total_results=5,
            unique_papers=5,
            unique_sections=3,
        )
        assert not report.is_acceptable()

    def test_is_acceptable_fails_diversity(self):
        report = VerificationReport(
            avg_relevance_score=0.8,
            diversity_score=0.1,
            recency_score=0.7,
            total_sources=1,
            total_results=5,
            unique_papers=1,
            unique_sections=3,
        )
        assert not report.is_acceptable()

    def test_is_acceptable_fails_total_results(self):
        report = VerificationReport(
            avg_relevance_score=0.8,
            diversity_score=0.5,
            recency_score=0.7,
            total_sources=2,
            total_results=2,
            unique_papers=2,
            unique_sections=1,
        )
        assert not report.is_acceptable()
