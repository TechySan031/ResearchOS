"""Literature review agent node — synthesizes papers into a thematic review."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry, _papers_context
from app.agents.prompts.literature_review import LITERATURE_REVIEW_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def literature_review_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: synthesize a literature review from retrieved papers.

    Uses Kimi (128K context) to handle large volumes of paper abstracts
    and produce a thematic, citation-grounded review.
    """
    project_id = state.get("project_id", "")
    papers = state.get("retrieved_papers", [])
    topic = state.get("topic", "")
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("literature_review.start", project_id=project_id, paper_count=len(papers))
    await publish_event("literature_review", "started", project_id, {"paper_count": len(papers)})

    if not papers:
        return {
            "literature_review": "No papers available for review.",
            "key_themes": [],
            "current_agent": "literature_review",
            "agent_history": [make_history_entry("literature_review", "skipped", reason="no_papers")],
            "status": "review_skipped",
        }

    context = _papers_context(papers)
    user_prompt = (
        f"## Research Topic\n{topic}\n\n"
        f"## Papers to Review ({len(papers)} papers)\n\n{context}"
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="kimi",
            system_prompt=LITERATURE_REVIEW_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=8192,
        )
    except Exception as e:
        logger.error("literature_review.llm_error", error=str(e))
        return {
            "current_agent": "literature_review",
            "agent_history": [make_history_entry("literature_review", "failed")],
            "errors": [make_error_entry("literature_review", str(e))],
            "literature_review": f"Literature review generation failed: {e}",
            "key_themes": [],
        }

    review_text = result.get("literature_review", str(result))
    themes = result.get("key_themes", [])
    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    await publish_event("literature_review", "completed", project_id, {
        "themes_count": len(themes), "review_length": len(review_text), "elapsed": elapsed,
    })
    logger.info("literature_review.complete", themes=len(themes), elapsed=elapsed)

    return {
        "literature_review": review_text,
        "key_themes": themes,
        "current_agent": "literature_review",
        "agent_history": [make_history_entry("literature_review", themes_count=len(themes), elapsed=elapsed)],
        "status": "review_complete",
    }
