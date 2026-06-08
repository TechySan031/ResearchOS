"""Tests for the deterministic supervisor routing logic.

The supervisor is the BRAIN of the system — these tests are critical.
They verify every routing rule in isolation.
"""

import pytest

from app.agents.supervisor import route


def _make_state(**overrides) -> dict:
    """Create a minimal ResearchState dict with defaults."""
    base = {
        "topic": "test topic",
        "project_id": "test-proj-001",
        "retrieved_papers": [],
        "literature_review": "",
        "citation_verification_results": [],
        "research_gaps": [],
        "suggested_methodologies": [],
        "selected_methodology": None,
        "paper_sections": {},
        "hallucination_report": {},
        "formatted_paper": "",
        "journal_recommendations": [],
        "reviewer_feedback": [],
        "submission_package": {},
        "revision_count": 0,
        "max_revisions": 3,
    }
    base.update(overrides)
    return base


class TestSupervisorRouting:
    """Test all 14 deterministic routing rules."""

    # ── Rule 1: No papers → research_retrieval ──

    def test_empty_state_routes_to_retrieval(self):
        state = _make_state()
        assert route(state) == "research_retrieval"

    # ── Rule 2: Papers retrieved → literature_review ──

    def test_papers_no_review_routes_to_literature_review(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
        )
        assert route(state) == "literature_review"

    # ── Rule 3: Review done → citation_verification ──

    def test_review_done_routes_to_citation_verification(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
        )
        assert route(state) == "citation_verification"

    # ── Rule 4: Citations verified → gap_analysis ──

    def test_citations_verified_routes_to_gap_analysis(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
        )
        assert route(state) == "gap_analysis"

    # ── Rule 5: Gaps found → methodology_suggestion ──

    def test_gaps_found_routes_to_methodology(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
        )
        assert route(state) == "methodology_suggestion"

    # ── Rule 6: Methodology selected → draft_writing ──

    def test_methodology_selected_routes_to_draft(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
        )
        assert route(state) == "draft_writing"

    # ── Rule 7: Draft exists → hallucination_detection ──

    def test_draft_routes_to_hallucination_check(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract", "introduction": "Test intro"},
        )
        assert route(state) == "hallucination_detection"

    # ── Rule 8: Hallucination score > 0.3 → back to draft_writing ──

    def test_high_hallucination_routes_back_to_draft(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract"},
            hallucination_report={"score": 0.5},
            revision_count=0,
        )
        assert route(state) == "draft_writing"

    def test_high_hallucination_stops_at_max_revisions(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract"},
            hallucination_report={"score": 0.5},
            revision_count=3,  # At max
        )
        # Should proceed to formatting despite high score
        assert route(state) == "formatting"

    # ── Rule 9: Hallucination OK → formatting ──

    def test_low_hallucination_routes_to_formatting(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract"},
            hallucination_report={"score": 0.1},
        )
        assert route(state) == "formatting"

    # ── Rule 10: Formatted → journal_recommendation ──

    def test_formatted_routes_to_journal(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract"},
            hallucination_report={"score": 0.1},
            formatted_paper="\\documentclass{article}...",
        )
        assert route(state) == "journal_recommendation"

    # ── Rule 11: Journals → reviewer_simulation ──

    def test_journals_recommended_routes_to_reviewer(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract"},
            hallucination_report={"score": 0.1},
            formatted_paper="\\documentclass{article}...",
            journal_recommendations=[{"name": "NeurIPS"}],
        )
        assert route(state) == "reviewer_simulation"

    # ── Rule 12: Low review score → revision loop ──

    def test_low_review_score_routes_back_to_draft(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract"},
            hallucination_report={"score": 0.1},
            formatted_paper="\\documentclass{article}...",
            journal_recommendations=[{"name": "NeurIPS"}],
            reviewer_feedback=[{"score": 4.5}],
            revision_count=0,
        )
        assert route(state) == "draft_writing"

    # ── Rule 13: Good review → submission_preparation ──

    def test_good_review_routes_to_submission(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract"},
            hallucination_report={"score": 0.1},
            formatted_paper="\\documentclass{article}...",
            journal_recommendations=[{"name": "NeurIPS"}],
            reviewer_feedback=[{"score": 7.5}],
        )
        assert route(state) == "submission_preparation"

    # ── Rule 14: Everything complete → END ──

    def test_complete_state_routes_to_end(self):
        state = _make_state(
            retrieved_papers=[{"title": "Paper 1"}],
            literature_review="A comprehensive review...",
            citation_verification_results=[{"status": "verified"}],
            research_gaps=[{"title": "Gap 1"}],
            suggested_methodologies=[{"name": "Method A"}],
            selected_methodology={"name": "Method A"},
            paper_sections={"abstract": "Test abstract"},
            hallucination_report={"score": 0.1},
            formatted_paper="\\documentclass{article}...",
            journal_recommendations=[{"name": "NeurIPS"}],
            reviewer_feedback=[{"score": 7.5}],
            submission_package={"cover_letter": "Dear Editor..."},
        )
        assert route(state) == "END"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_revision_count_at_boundary(self):
        """revision_count == max_revisions should NOT trigger re-draft."""
        state = _make_state(
            retrieved_papers=[{"title": "P1"}],
            literature_review="Review",
            citation_verification_results=[{"s": "v"}],
            research_gaps=[{"g": "1"}],
            suggested_methodologies=[{"m": "1"}],
            selected_methodology={"m": "1"},
            paper_sections={"abstract": "A"},
            hallucination_report={"score": 0.5},
            revision_count=3,
            max_revisions=3,
        )
        # At max_revisions, skip re-draft and proceed
        assert route(state) != "draft_writing"

    def test_reviewer_score_exactly_six(self):
        """Score == 6.0 should NOT trigger revision (threshold is < 6.0)."""
        state = _make_state(
            retrieved_papers=[{"title": "P1"}],
            literature_review="Review",
            citation_verification_results=[{"s": "v"}],
            research_gaps=[{"g": "1"}],
            suggested_methodologies=[{"m": "1"}],
            selected_methodology={"m": "1"},
            paper_sections={"abstract": "A"},
            hallucination_report={"score": 0.1},
            formatted_paper="Formatted",
            journal_recommendations=[{"j": "1"}],
            reviewer_feedback=[{"score": 6.0}],
        )
        assert route(state) == "submission_preparation"

    def test_hallucination_score_exactly_threshold(self):
        """score == 0.3 should NOT trigger re-draft (threshold is > 0.3)."""
        state = _make_state(
            retrieved_papers=[{"title": "P1"}],
            literature_review="Review",
            citation_verification_results=[{"s": "v"}],
            research_gaps=[{"g": "1"}],
            suggested_methodologies=[{"m": "1"}],
            selected_methodology={"m": "1"},
            paper_sections={"abstract": "A"},
            hallucination_report={"score": 0.3},
        )
        assert route(state) == "formatting"

    def test_missing_score_in_hallucination_report(self):
        """Report without 'score' key should default to 0.0."""
        state = _make_state(
            retrieved_papers=[{"title": "P1"}],
            literature_review="Review",
            citation_verification_results=[{"s": "v"}],
            research_gaps=[{"g": "1"}],
            suggested_methodologies=[{"m": "1"}],
            selected_methodology={"m": "1"},
            paper_sections={"abstract": "A"},
            hallucination_report={"details": "no score"},
        )
        assert route(state) == "formatting"

    def test_non_numeric_reviewer_scores_ignored(self):
        """Reviewer entries without numeric scores are skipped."""
        state = _make_state(
            retrieved_papers=[{"title": "P1"}],
            literature_review="Review",
            citation_verification_results=[{"s": "v"}],
            research_gaps=[{"g": "1"}],
            suggested_methodologies=[{"m": "1"}],
            selected_methodology={"m": "1"},
            paper_sections={"abstract": "A"},
            hallucination_report={"score": 0.1},
            formatted_paper="F",
            journal_recommendations=[{"j": "1"}],
            reviewer_feedback=[{"score": "invalid"}, {"not_a_score": True}],
        )
        # With no valid scores, avg is 0.0 which is < 6.0
        # but revision_count < max_revisions, so routes to draft_writing
        assert route(state) == "draft_writing"
