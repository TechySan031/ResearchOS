"""Formatting agent node — applies academic style formatting."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry, _papers_context
from app.agents.prompts.formatting import FORMATTING_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def formatting_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: format the paper in IEEE/ACM/Springer style."""
    project_id = state.get("project_id", "")
    sections = state.get("paper_sections", {})
    format_style = state.get("format_style", "ieee")
    papers = state.get("retrieved_papers", [])
    citations = state.get("citations", [])
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("formatting.start", project_id=project_id, style=format_style)
    await publish_event("formatting", "started", project_id, {"style": format_style})

    draft_text = ""
    for name, content in sections.items():
        draft_text += f"\n\n## {name}\n{content}"

    # Build citation list for bibliography
    cit_text = "\n".join(
        f"[REF_{i+1}] {c.get('paper_title', '')} by {', '.join(c.get('authors', [])[:3])} "
        f"({c.get('year', 'n.d.')}). DOI: {c.get('doi', 'N/A')}"
        for i, c in enumerate(citations[:30])
    ) or "\n".join(
        f"[REF_{i+1}] {p.get('title', '')} ({p.get('year', 'n.d.')}). DOI: {p.get('doi', 'N/A')}"
        for i, p in enumerate(papers[:30])
    )

    user_prompt = (
        f"## Target Format Style: {format_style.upper()}\n\n"
        f"## Paper Draft\n{draft_text[:10000]}\n\n"
        f"## Citation List\n{cit_text}"
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="mistral",
            system_prompt=FORMATTING_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=10000,
        )
    except Exception as e:
        logger.error("formatting.llm_error", error=str(e))
        return {
            "formatted_paper": draft_text,
            "current_agent": "formatting",
            "agent_history": [make_history_entry("formatting", "failed")],
            "errors": [make_error_entry("formatting", str(e))],
        }

    formatted = result.get("formatted_paper", draft_text)
    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    await publish_event("formatting", "completed", project_id, {"style": format_style, "length": len(formatted), "elapsed": elapsed})
    logger.info("formatting.complete", style=format_style, elapsed=elapsed)

    return {
        "formatted_paper": formatted,
        "current_agent": "formatting",
        "agent_history": [make_history_entry("formatting", style=format_style, elapsed=elapsed)],
        "status": "paper_formatted",
    }
