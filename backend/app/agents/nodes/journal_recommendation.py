"""Journal recommendation agent node — suggests target venues."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry
from app.agents.prompts.journal import JOURNAL_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def journal_recommendation_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: recommend journals and conferences for submission."""
    project_id = state.get("project_id", "")
    topic = state.get("topic", "")
    sections = state.get("paper_sections", {})
    key_themes = state.get("key_themes", [])
    papers = state.get("retrieved_papers", [])
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("journal_recommendation.start", project_id=project_id)
    await publish_event("journal_recommendation", "started", project_id)

    abstract = sections.get("abstract", "")
    # Gather venues from retrieved papers for context
    venues = list({p.get("venue", "") for p in papers if p.get("venue")})[:15]

    user_prompt = (
        f"## Research Topic\n{topic}\n\n"
        f"## Paper Abstract\n{abstract[:1500]}\n\n"
        f"## Key Themes\n" + "\n".join(f"- {t}" for t in key_themes) + "\n\n"
        f"## Venues from Related Literature\n" + "\n".join(f"- {v}" for v in venues)
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="mistral",
            system_prompt=JOURNAL_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4096,
        )
    except Exception as e:
        logger.error("journal_recommendation.llm_error", error=str(e))
        return {
            "journal_recommendations": [],
            "current_agent": "journal_recommendation",
            "agent_history": [make_history_entry("journal_recommendation", "failed")],
            "errors": [make_error_entry("journal_recommendation", str(e))],
        }

    recommendations = result.get("journal_recommendations", [])
    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    await publish_event("journal_recommendation", "completed", project_id, {"count": len(recommendations), "elapsed": elapsed})
    logger.info("journal_recommendation.complete", count=len(recommendations), elapsed=elapsed)

    return {
        "journal_recommendations": recommendations,
        "current_agent": "journal_recommendation",
        "agent_history": [make_history_entry("journal_recommendation", count=len(recommendations), elapsed=elapsed)],
        "status": "journals_recommended",
    }
