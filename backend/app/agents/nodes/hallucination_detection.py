"""Hallucination detection agent node — verifies claims against sources."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry, _papers_context
from app.agents.prompts.hallucination import HALLUCINATION_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def hallucination_detection_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: detect hallucinations in the paper draft.

    Uses Mistral to cross-reference every claim in the draft against
    the source papers. Returns a hallucination report with score.
    If score > 0.3, the supervisor routes back to draft_writing.
    """
    project_id = state.get("project_id", "")
    sections = state.get("paper_sections", {})
    papers = state.get("retrieved_papers", [])
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("hallucination_detection.start", project_id=project_id, sections=len(sections))
    await publish_event("hallucination_detection", "started", project_id)

    # Combine all sections for analysis
    draft_text = ""
    for name, content in sections.items():
        draft_text += f"\n\n## {name}\n{content}"

    papers_ctx = _papers_context(papers, max_papers=20)
    user_prompt = (
        f"## Paper Draft to Analyze\n{draft_text[:10000]}\n\n"
        f"## Source Papers (ground truth)\n{papers_ctx}"
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="mistral",
            system_prompt=HALLUCINATION_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=6000,
        )
    except Exception as e:
        logger.error("hallucination_detection.llm_error", error=str(e))
        return {
            "hallucination_report": {"score": 0.0, "error": str(e)},
            "current_agent": "hallucination_detection",
            "agent_history": [make_history_entry("hallucination_detection", "failed")],
            "errors": [make_error_entry("hallucination_detection", str(e))],
        }

    report = result.get("hallucination_report", result)
    if isinstance(report, str):
        report = {"score": 0.0, "raw": report}

    score = float(report.get("score", 0.0))
    flagged = report.get("flagged_claims", [])
    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    needs_revision = score > 0.3

    await publish_event("hallucination_detection", "completed", project_id, {
        "score": score, "flagged_count": len(flagged), "needs_revision": needs_revision, "elapsed": elapsed,
    })
    logger.info("hallucination_detection.complete", score=score, flagged=len(flagged), needs_revision=needs_revision)

    return {
        "hallucination_report": report,
        "current_agent": "hallucination_detection",
        "agent_history": [make_history_entry(
            "hallucination_detection", score=score, flagged_count=len(flagged), needs_revision=needs_revision, elapsed=elapsed,
        )],
        "status": "hallucination_checked",
    }
