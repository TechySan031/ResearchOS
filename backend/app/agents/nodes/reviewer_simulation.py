"""Reviewer simulation agent node — simulates peer review."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry
from app.agents.prompts.reviewer import REVIEWER_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def reviewer_simulation_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: simulate peer review with 3 AI reviewers.

    Uses Kimi for long-context review of the full paper. Returns
    structured feedback with scores. If avg score < 6, the supervisor
    routes back to draft_writing for revision.
    """
    project_id = state.get("project_id", "")
    formatted_paper = state.get("formatted_paper", "")
    sections = state.get("paper_sections", {})
    topic = state.get("topic", "")
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("reviewer_simulation.start", project_id=project_id)
    await publish_event("reviewer_simulation", "started", project_id)

    paper_text = formatted_paper or "\n\n".join(f"## {k}\n{v}" for k, v in sections.items())

    user_prompt = (
        f"## Research Topic\n{topic}\n\n"
        f"## Full Paper\n{paper_text[:12000]}"
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="kimi",
            system_prompt=REVIEWER_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,
            max_tokens=8000,
        )
    except Exception as e:
        logger.error("reviewer_simulation.llm_error", error=str(e))
        return {
            "reviewer_feedback": [{"reviewer_id": "R1", "score": 7.0, "decision": "minor_revision",
                                   "error": str(e), "strengths": [], "weaknesses": []}],
            "current_agent": "reviewer_simulation",
            "agent_history": [make_history_entry("reviewer_simulation", "failed")],
            "errors": [make_error_entry("reviewer_simulation", str(e))],
        }

    feedback = result.get("reviewer_feedback", [])
    meta = result.get("meta_review", {})
    avg_score = meta.get("avg_score", 0)
    if not avg_score and feedback:
        scores = [f.get("score", 0) for f in feedback if isinstance(f.get("score"), (int, float))]
        avg_score = sum(scores) / len(scores) if scores else 0

    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()
    needs_revision = avg_score < 6.0

    await publish_event("reviewer_simulation", "completed", project_id, {
        "avg_score": avg_score, "reviewers": len(feedback), "needs_revision": needs_revision, "elapsed": elapsed,
    })
    logger.info("reviewer_simulation.complete", avg_score=avg_score, needs_revision=needs_revision, elapsed=elapsed)

    return {
        "reviewer_feedback": feedback,
        "current_agent": "reviewer_simulation",
        "agent_history": [make_history_entry(
            "reviewer_simulation", avg_score=avg_score, needs_revision=needs_revision, elapsed=elapsed,
        )],
        "status": "review_simulated",
    }
