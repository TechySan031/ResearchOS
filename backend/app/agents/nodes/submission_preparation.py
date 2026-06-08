"""Submission preparation agent node — builds the submission package."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry
from app.agents.prompts.submission import SUBMISSION_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def submission_preparation_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: prepare the final submission package.

    Generates cover letter, author statement, keywords, highlights,
    and a submission readiness checklist.
    """
    project_id = state.get("project_id", "")
    formatted_paper = state.get("formatted_paper", "")
    sections = state.get("paper_sections", {})
    topic = state.get("topic", "")
    journal_recs = state.get("journal_recommendations", [])
    reviewer_feedback = state.get("reviewer_feedback", [])
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("submission_preparation.start", project_id=project_id)
    await publish_event("submission_preparation", "started", project_id)

    target_journal = journal_recs[0].get("name", "Target Journal") if journal_recs else "Target Journal"

    paper_text = formatted_paper or "\n\n".join(f"## {k}\n{v}" for k, v in sections.items())
    abstract = sections.get("abstract", "")

    review_summary = ""
    if reviewer_feedback:
        scores = [f.get("score", 0) for f in reviewer_feedback]
        avg = sum(scores) / len(scores) if scores else 0
        review_summary = f"Average reviewer score: {avg:.1f}/10"

    user_prompt = (
        f"## Research Topic\n{topic}\n\n"
        f"## Target Journal/Conference\n{target_journal}\n\n"
        f"## Paper Abstract\n{abstract[:1000]}\n\n"
        f"## Full Paper (summary)\n{paper_text[:5000]}\n\n"
        f"## Review Summary\n{review_summary}"
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="mistral",
            system_prompt=SUBMISSION_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4096,
        )
    except Exception as e:
        logger.error("submission_preparation.llm_error", error=str(e))
        return {
            "submission_package": {"error": str(e), "submission_ready": False},
            "current_agent": "submission_preparation",
            "agent_history": [make_history_entry("submission_preparation", "failed")],
            "errors": [make_error_entry("submission_preparation", str(e))],
        }

    package = result.get("submission_package", result)
    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    await publish_event("submission_preparation", "completed", project_id, {
        "ready": package.get("submission_ready", False), "target": target_journal, "elapsed": elapsed,
    })
    logger.info("submission_preparation.complete", ready=package.get("submission_ready", False), elapsed=elapsed)

    return {
        "submission_package": package,
        "current_agent": "submission_preparation",
        "agent_history": [make_history_entry("submission_preparation", ready=package.get("submission_ready", False), elapsed=elapsed)],
        "status": "completed",
    }
