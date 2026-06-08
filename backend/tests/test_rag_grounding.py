"""Tests for the citation grounding module.

Tests the pure logic of grounding classification and sentence extraction.
LLM-dependent tests are mocked.
"""

import pytest

from app.rag.grounding import (
    CitationGrounder,
    GroundingLevel,
    GroundingResult,
    SectionGroundingReport,
)


class TestGroundingLevel:
    """Test grounding level classification."""

    @pytest.fixture
    def grounder(self):
        return CitationGrounder()

    def test_strong_threshold(self, grounder):
        assert grounder._classify_score(0.85) == GroundingLevel.STRONG
        assert grounder._classify_score(0.80) == GroundingLevel.STRONG

    def test_moderate_threshold(self, grounder):
        assert grounder._classify_score(0.75) == GroundingLevel.MODERATE
        assert grounder._classify_score(0.65) == GroundingLevel.MODERATE

    def test_weak_threshold(self, grounder):
        assert grounder._classify_score(0.60) == GroundingLevel.WEAK
        assert grounder._classify_score(0.50) == GroundingLevel.WEAK

    def test_ungrounded_threshold(self, grounder):
        assert grounder._classify_score(0.49) == GroundingLevel.UNGROUNDED
        assert grounder._classify_score(0.0) == GroundingLevel.UNGROUNDED


class TestCitedSentenceExtraction:
    """Test extraction of sentences with [REF_n] markers."""

    @pytest.fixture
    def grounder(self):
        return CitationGrounder()

    def test_extracts_single_citation(self, grounder):
        text = "This method achieves 95% accuracy [REF_1]. No other method compares."
        results = grounder._extract_cited_sentences(text)
        assert len(results) == 1
        claim, key = results[0]
        assert key == "REF_1"
        assert "[REF_1]" not in claim  # Marker should be removed

    def test_extracts_multiple_citations(self, grounder):
        text = (
            "Transformers revolutionized NLP [REF_1]. "
            "Later work extended them to vision [REF_2]. "
            "This remains an open area."
        )
        results = grounder._extract_cited_sentences(text)
        assert len(results) == 2
        keys = {r[1] for r in results}
        assert keys == {"REF_1", "REF_2"}

    def test_no_citations(self, grounder):
        text = "This sentence has no citations. Neither does this one."
        results = grounder._extract_cited_sentences(text)
        assert len(results) == 0

    def test_citation_in_middle_of_sentence(self, grounder):
        text = "The model [REF_3] achieves state of the art."
        results = grounder._extract_cited_sentences(text)
        assert len(results) == 1
        assert results[0][1] == "REF_3"

    def test_double_digit_ref(self, grounder):
        text = "Prior work [REF_15] showed this."
        results = grounder._extract_cited_sentences(text)
        assert len(results) == 1
        assert results[0][1] == "REF_15"


class TestSectionGroundingReport:
    """Test the report aggregation logic."""

    def test_grounding_ratio_all_strong(self):
        report = SectionGroundingReport(
            section_name="intro",
            total_claims=5,
            strong_count=5,
        )
        assert report.grounding_ratio == 1.0

    def test_grounding_ratio_mixed(self):
        report = SectionGroundingReport(
            section_name="intro",
            total_claims=10,
            strong_count=3,
            moderate_count=4,
            weak_count=2,
            ungrounded_count=1,
        )
        assert report.grounding_ratio == 0.7  # (3+4)/10

    def test_grounding_ratio_no_claims(self):
        report = SectionGroundingReport(
            section_name="empty",
            total_claims=0,
        )
        assert report.grounding_ratio == 1.0  # No claims = fully grounded

    def test_grounding_ratio_all_ungrounded(self):
        report = SectionGroundingReport(
            section_name="bad",
            total_claims=5,
            ungrounded_count=5,
        )
        assert report.grounding_ratio == 0.0


class TestGroundingResult:
    """Test the GroundingResult dataclass."""

    def test_creation(self):
        result = GroundingResult(
            claim_text="Transformers are effective",
            source_text="We show transformers achieve...",
            source_paper_id="p1",
            source_doi="10.1234/test",
            similarity_score=0.85,
            grounding_level=GroundingLevel.STRONG,
            citation_key="REF_1",
        )
        assert result.grounding_level == GroundingLevel.STRONG
        assert result.similarity_score == 0.85

    def test_defaults(self):
        result = GroundingResult(
            claim_text="test",
            source_text="",
            source_paper_id="",
            source_doi="",
            similarity_score=0.0,
            grounding_level=GroundingLevel.UNGROUNDED,
        )
        assert result.citation_key == ""
        assert result.source_title == ""
        assert result.source_section == ""
