"""Gap analysis agent node — identifies research gaps from the literature."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry
from app.agents.prompts.gap_analysis import GAP_ANALYSIS_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def gap_analysis_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: identify research gaps from the literature review."""
    project_id = state.get("project_id", "")
    review = state.get("literature_review", "")
    themes = state.get("key_themes", [])
    topic = state.get("topic", "")
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("gap_analysis.start", project_id=project_id)
    await publish_event("gap_analysis", "started", project_id)

    user_prompt = (
        f"## Research Topic\n{topic}\n\n"
        f"## Key Themes Identified\n" + "\n".join(f"- {t}" for t in themes) + "\n\n"
        f"## Literature Review\n{review[:8000]}"
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="mistral",
            system_prompt=GAP_ANALYSIS_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4096,
        )
        logger.info(
            "gap_analysis.raw_result",
            result=result
            
        )
    except Exception as e:
        logger.error("gap_analysis.llm_error", error=str(e))
        return {
            "current_agent": "gap_analysis",
            "agent_history": [make_history_entry("gap_analysis", "failed")],
            "errors": [make_error_entry("gap_analysis", str(e))],
            "research_gaps": [],
        }

    gaps = result.get("research_gaps", [])
    logger.info(
        "gap_analysis.gaps_count",
        count=len(gaps)
    )
    print("\nGAPS COUNT=", len(gaps), "\n")
    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    await publish_event("gap_analysis", "completed", project_id, {"gap_count": len(gaps), "elapsed": elapsed})
    logger.info("gap_analysis.complete", gap_count=len(gaps), elapsed=elapsed)

    return {
        "research_gaps": gaps,
        "gap_analysis_completed": True, 
        "current_agent": "gap_analysis",
        "agent_history": [make_history_entry("gap_analysis", gap_count=len(gaps), elapsed=elapsed)],
        "status": "gaps_identified",
    }
