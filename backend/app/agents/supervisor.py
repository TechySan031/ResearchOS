"""Deterministic supervisor — routes the workflow to the next agent node.

Unlike LLM-based supervisors, this module applies hard-coded routing
rules so that the pipeline is **reproducible**, **auditable**, and
**fast**.  Every routing decision is logged via structlog.
"""

from __future__ import annotations

import datetime as _dt
from typing import Literal

from app.agents.state import ResearchState
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Valid node names ────────────────────────────────────────────────────
_NODE_NAMES = Literal[
    "research_retrieval",
    "literature_review",
    "citation_verification",
    "gap_analysis",
    "methodology_suggestion",
    "draft_writing",
    "hallucination_detection",
    "formatting",
    "journal_recommendation",
    "reviewer_simulation",
    "submission_preparation",
    "END",
]


def _avg_reviewer_score(feedback: list[dict]) -> float:
    """Compute average score from reviewer feedback dicts.

    Each dict is expected to carry a ``"score"`` key with a numeric
    value.  Missing / non-numeric entries are silently skipped.
    """
    scores: list[float] = []
    for entry in feedback:
        try:
            scores.append(float(entry["score"]))
        except (KeyError, TypeError, ValueError):
            continue
    return sum(scores) / len(scores) if scores else 0.0


def _hallucination_score(report: dict) -> float:
    """Extract the hallucination score from a report dict.

    Falls back to ``0.0`` if the key is absent or non-numeric.
    """
    try:
        return float(report.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def route(state: ResearchState) -> str:
    """Determine the next node to execute based on the current state.

    The routing rules are evaluated **in order**.  The first matching rule
    wins.

    Args:
        state: The current workflow state.

    Returns:
        Name of the next LangGraph node (or ``"END"``).
    """

    retrieved_papers = state.get("retrieved_papers") or []
    literature_review = state.get("literature_review") or ""
    citation_results = state.get("citation_verification_results") or []
    research_gaps = state.get("research_gaps") or []
    suggested_meths = state.get("suggested_methodologies") or []
    selected_meth = state.get("selected_methodology")
    paper_sections = state.get("paper_sections") or {}
    hallucination_report = state.get("hallucination_report") or {}
    formatted_paper = state.get("formatted_paper") or ""
    journal_recs = state.get("journal_recommendations") or []
    reviewer_fb = state.get("reviewer_feedback") or []
    submission_pkg = state.get("submission_package") or {}
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 3)

    next_node: str

    # 1. No papers → retrieval
    if not retrieved_papers:
        next_node = "research_retrieval"

    # 2. Papers but no review
    elif not literature_review:
        next_node = "literature_review"

    # 3. Review exists but citations not verified
    elif not citation_results:
        next_node = "citation_verification"

    # 4. Citations verified but no gap analysis
    elif not research_gaps: 
        next_node = "gap_analysis"

    # 5. Gaps found but no methodology suggested
    elif not suggested_meths and selected_meth is None:
        next_node = "methodology_suggestion"

    # 6. Methodology selected but no draft
    elif not paper_sections:
        next_node = "draft_writing"

    # 7. Draft exists but not checked for hallucinations
    elif not hallucination_report:
        next_node = "hallucination_detection"

    # 8. Hallucination score too high → revise draft (max 3 times)
    elif (
        _hallucination_score(hallucination_report) > 0.3
        and revision_count < 3
    ):
        next_node = "draft_writing"

    # 9. Hallucination OK but not formatted
    elif not formatted_paper:
        next_node = "formatting"

    # 10. Formatted but no journal recommendations
    elif not journal_recs:
        next_node = "journal_recommendation"

    # 11. Journals recommended but no reviews yet
    elif not reviewer_fb:
        next_node = "reviewer_simulation"

    # 12. Low review score → revise (within max_revisions budget)
    elif _avg_reviewer_score(reviewer_fb) < 6.0 and revision_count < max_revisions:
        next_node = "draft_writing"

    # 13. Reviews OK but no submission package
    elif not submission_pkg:
        next_node = "submission_preparation"

    # 14. Everything complete
    else:
        next_node = "END"

    _reason = _describe_reason(next_node, state)

    logger.info(
        "supervisor.route",
        next_node=next_node,
        revision_count=revision_count,
        reason=_reason,
        project_id=state.get("project_id"),
    )

    return next_node


def _describe_reason(next_node: str, state: ResearchState) -> str:
    """Return a human-readable reason for the routing decision."""
    reasons: dict[str, str] = {
        "research_retrieval": "No papers retrieved yet",
        "literature_review": "Papers retrieved; literature review pending",
        "citation_verification": "Literature review done; citations unverified",
        "gap_analysis": "Citations verified; gap analysis pending",
        "methodology_suggestion": "Gaps identified; methodology suggestion pending",
        "draft_writing": _draft_writing_reason(state),
        "hallucination_detection": "Draft exists; hallucination check pending",
        "formatting": "Hallucination check passed; formatting pending",
        "journal_recommendation": "Paper formatted; journal recommendation pending",
        "reviewer_simulation": "Journals recommended; reviewer simulation pending",
        "submission_preparation": "Reviews satisfactory; submission preparation pending",
        "END": "Submission package ready — workflow complete",
    }
    return reasons.get(next_node, "Unknown")


def _draft_writing_reason(state: ResearchState) -> str:
    """Determine why the draft_writing node is being invoked."""
    hallucination_report = state.get("hallucination_report") or {}
    reviewer_fb = state.get("reviewer_feedback") or []
    revision_count = state.get("revision_count", 0)

    h_score = _hallucination_score(hallucination_report)
    if h_score > 0.3:
        return (
            f"Hallucination score {h_score:.2f} > 0.3; "
            f"revision {revision_count + 1}"
        )

    avg = _avg_reviewer_score(reviewer_fb)
    if reviewer_fb and avg < 6.0:
        return (
            f"Avg reviewer score {avg:.1f} < 6.0; "
            f"revision {revision_count + 1}"
        )

    return "Methodology selected; initial draft pending"
