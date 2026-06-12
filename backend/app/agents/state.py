"""ResearchState — LangGraph shared state definition.

Defines the typed dictionary that flows through every node in the
multi-agent research workflow graph.  Annotated fields use LangGraph
reducers so that successive node outputs are *merged* rather than
overwritten (e.g. ``messages`` uses ``add_messages``).
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

# pyrefly: ignore [missing-import]
from langgraph.graph.message import add_messages


def _append_list(existing: list, new: list) -> list:
    """Reducer that appends new items to an existing list."""
    if existing is None:
        existing = []
    if new is None:
        new = []
    return existing + new


class ResearchState(TypedDict, total=False):
    """Shared state passed between all LangGraph nodes.

    Fields annotated with a reducer are *accumulated* across node calls.
    All other fields are overwritten by the latest node output.

    Attributes:
        topic: The research topic / question supplied by the user.
        project_id: UUID of the owning project.
        user_preferences: Free-form dict of user-specified preferences
            (e.g. target journal, language style).
        retrieved_papers: Papers returned by the retrieval node.
        paper_embeddings_stored: Whether the paper vectors have been
            persisted to the vector store.
        literature_review: Markdown text of the synthesised literature
            review.
        key_themes: High-level themes extracted from the literature.
        citations: Structured citation objects used throughout the paper.
        citation_verification_results: Per-citation verification verdicts.
        research_gaps: Identified gaps in the existing literature.
        suggested_methodologies: Methodologies suggested by the gap
            analysis agent.
        selected_methodology: The methodology chosen for the paper.
        paper_outline: Hierarchical outline dict for the paper.
        paper_sections: Mapping of section title → Markdown body text.
        hallucination_report: Results from hallucination detection.
        formatted_paper: Final formatted paper text (LaTeX / Markdown).
        format_style: Desired formatting style (e.g. ``"ieee"``,
            ``"apa"``).
        journal_recommendations: Ranked list of suitable journals.
        reviewer_feedback: Simulated reviewer comments / scores.
        submission_package: Metadata + artefacts for journal submission.
        current_agent: Name of the agent currently executing.
        agent_history: Append-only log of agent execution records.
        errors: Append-only list of error dicts.
        status: Current workflow status string.
        messages: LangGraph chat messages (accumulated via
            ``add_messages``).
        revision_count: How many revision loops have occurred.
        max_revisions: Upper bound on revision loops.
    """

    # ── User inputs ──────────────────────────────────────────────
    topic: str
    project_id: str
    user_preferences: dict

    # ── Retrieval ────────────────────────────────────────────────
    retrieved_papers: list[dict]
    paper_embeddings_stored: bool

    # ── Literature review ────────────────────────────────────────
    literature_review: str
    key_themes: list[str]

    # ── Citations ────────────────────────────────────────────────
    citations: list[dict]
    citation_verification_results: list[dict]

    # ── Gap analysis ─────────────────────────────────────────────
    research_gaps: list[dict]
    gap_analysis_completed: bool

    # ── Methodology ──────────────────────────────────────────────
    suggested_methodologies: list[dict]
    selected_methodology: dict | None

    # ── Paper drafting ───────────────────────────────────────────
    paper_outline: dict
    paper_sections: dict[str, str]

    # ── Hallucination detection ──────────────────────────────────
    hallucination_report: dict

    # ── Formatting ───────────────────────────────────────────────
    formatted_paper: str
    format_style: str

    # ── Journal & review ─────────────────────────────────────────
    journal_recommendations: list[dict]
    reviewer_feedback: list[dict]

    # ── Submission ───────────────────────────────────────────────
    submission_package: dict

    # ── Workflow meta ────────────────────────────────────────────
    current_agent: str
    agent_history: Annotated[list[dict], _append_list]
    errors: Annotated[list[dict], _append_list]
    status: str
    messages: Annotated[list, add_messages]

    # ── Revision control ─────────────────────────────────────────
    revision_count: int
    max_revisions: int
