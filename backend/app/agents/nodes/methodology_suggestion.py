"""Methodology suggestion agent node — proposes research approaches."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry
from app.agents.prompts.methodology import METHODOLOGY_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def methodology_suggestion_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: suggest methodologies based on gaps and literature."""
    project_id = state.get("project_id", "")
    gaps = state.get("research_gaps", [])
    review = state.get("literature_review", "")
    topic = state.get("topic", "")
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("methodology_suggestion.start", project_id=project_id, gap_count=len(gaps))
    await publish_event("methodology_suggestion", "started", project_id)

    gaps_text = "\n".join(
        f"- **{g.get('title', 'Gap')}** ({g.get('type', 'unknown')}): {g.get('description', '')}"
        for g in gaps
    )

    user_prompt = (
        f"## Research Topic\n{topic}\n\n"
        f"## Identified Research Gaps\n{gaps_text}\n\n"
        f"## Literature Review Summary\n{review[:4000]}"
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="mistral",
            system_prompt=METHODOLOGY_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4096,
        )
    except Exception as e:
        logger.error("methodology_suggestion.llm_error", error=str(e))
        return {
            "current_agent": "methodology_suggestion",
            "agent_history": [make_history_entry("methodology_suggestion", "failed")],
            "errors": [make_error_entry("methodology_suggestion", str(e))],
            "suggested_methodologies": [],
        }

    methodologies = result.get("suggested_methodologies", [])
    recommended = result.get("recommendation", "")
    selected = None
    for m in methodologies:
        if m.get("methodology_id") == recommended:
            selected = m
            break
    if not selected and methodologies:
        selected = methodologies[0]

    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    await publish_event("methodology_suggestion", "completed", project_id, {
        "count": len(methodologies), "selected": selected.get("name", "") if selected else "", "elapsed": elapsed,
    })
    logger.info("methodology_suggestion.complete", count=len(methodologies), elapsed=elapsed)

    return {
        "suggested_methodologies": methodologies,
        "selected_methodology": selected,
        "current_agent": "methodology_suggestion",
        "agent_history": [make_history_entry("methodology_suggestion", count=len(methodologies), elapsed=elapsed)],
        "status": "methodology_selected",
    }
