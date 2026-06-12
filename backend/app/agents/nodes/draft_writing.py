"""Draft writing agent node — generates structured paper sections."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import (
    publish_event, make_history_entry, make_error_entry,
    _papers_context, stream_llm_to_event_bus,
)
from app.agents.prompts.draft_writing import DRAFT_WRITING_PROMPT
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def draft_writing_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: write/revise the research paper draft.

    Uses Kimi (128K context) to generate all paper sections with
    inline citation markers. Handles both initial drafts and revisions
    based on hallucination or reviewer feedback.
    """
    project_id = state.get("project_id", "")
    topic = state.get("topic", "")
    review = state.get("literature_review", "")
    gaps = state.get("research_gaps", [])
    methodology = state.get("selected_methodology", {})
    papers = state.get("retrieved_papers", [])
    revision_count = state.get("revision_count", 0)
    hallucination_report = state.get("hallucination_report", {})
    reviewer_feedback = state.get("reviewer_feedback", [])
    existing_sections = state.get("paper_sections", {})
    start = _dt.datetime.now(_dt.timezone.utc)

    is_revision = revision_count > 0 and existing_sections
    mode = "revision" if is_revision else "initial"

    logger.info("draft_writing.start", project_id=project_id, mode=mode, revision=revision_count)
    await publish_event("draft_writing", "started", project_id, {"mode": mode, "revision": revision_count})

    # Build context
    papers_ctx = _papers_context(papers, max_papers=20)
    gaps_text = "\n".join(f"- {g.get('title', '')}: {g.get('description', '')}" for g in gaps[:5])
    meth_text = (
        f"**{methodology.get('name', 'TBD')}**: {methodology.get('description', 'No methodology selected.')}"
        if methodology else "No methodology selected."
    )

    user_prompt = (
        f"## Research Topic\n{topic}\n\n"
        f"## Literature Review\n{review[:5000]}\n\n"
        f"## Research Gaps\n{gaps_text}\n\n"
        f"## Selected Methodology\n{meth_text}\n\n"
        f"## Available Papers (for citations)\n{papers_ctx}\n"
    )

    if is_revision:
        # Add revision feedback
        revision_context = f"\n\n## REVISION REQUIRED\nThis is revision #{revision_count}. Address the following:\n\n"

        if hallucination_report and hallucination_report.get("score", 0) > 0.3:
            flagged = hallucination_report.get("flagged_claims", [])
            revision_context += "### Hallucination Issues:\n"
            for f in flagged[:10]:
                revision_context += f"- [{f.get('severity', 'medium')}] {f.get('claim_text', '')}: {f.get('suggestion', '')}\n"

        if reviewer_feedback:
            revision_context += "\n### Reviewer Feedback:\n"
            for fb in reviewer_feedback:
                revision_context += f"- Reviewer {fb.get('reviewer_id', '?')} (score: {fb.get('score', '?')}):\n"
                for w in fb.get("weaknesses", []):
                    revision_context += f"  - Weakness: {w}\n"
                for s in fb.get("suggestions", []):
                    revision_context += f"  - Suggestion: {s}\n"

        user_prompt += revision_context
        user_prompt += f"\n### Previous Draft Sections:\n"
        for section_name, section_text in existing_sections.items():
            user_prompt += f"\n#### {section_name}\n{section_text[:1000]}...\n"

    try:
        llm = LLMClient()

        logger.info(
            "draft_writing.prompt_size",
            prompt_chars=len(user_prompt),
        )
        
        # Stream draft content through the event bus so clients see
        # tokens arriving in real-time.  The helper falls back to
        # non-streaming generate() if the stream fails.
        raw_response = await stream_llm_to_event_bus(
            agent_name="draft_writing",
            project_id=project_id,
            section="draft",
            llm=llm,
            provider="mistral",
            system_prompt=DRAFT_WRITING_PROMPT + "\n\nRespond ONLY with valid JSON.",
            user_prompt=user_prompt,
            temperature=0.4,
            max_tokens=12000,
        )

        # Parse the streamed response as JSON
        import json as _json
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            result = _json.loads(cleaned)
            logger.info(
                "draft_writing.result_keys",
                keys=list(result.keys()) if isinstance(result, dict) else "not_dict",
            )

            logger.info(
                "draft_writing.result_preview",
                preview=str(result)[:2000],
            )
        except _json.JSONDecodeError as e:
            logger.error(
                "draft_writing.json_parse_error",
                error=str(e),
                response_preview=raw_response[:5000],
            )

            result = {
                "raw_response": raw_response,
                "parse_error": True,
            }

    except Exception as e:
        logger.error("draft_writing.llm_error", error=str(e))
        return {
            "current_agent": "draft_writing",
            "agent_history": [make_history_entry("draft_writing", "failed")],
            "errors": [make_error_entry("draft_writing", str(e))],
        }

    sections = (
       result.get("paper_sections")
       or result.get("sections")
       or {}
)
    if not sections:
        logger.error(
            "draft_writing.empty_sections",

        )
        sections = {
        "Introduction": f"Introduction to {topic}",
        "Literature Review": review[:3000],
        "Methodology": str(methodology),
        "Conclusion": f"Conclusion for {topic}",
    }

    outline = (
        result.get("paper_outline")
        or result.get("outline")
        or {}
    )
    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    total_words = sum(len(s.split()) for s in sections.values())
    
    logger.info(
        "draft_writing.parsed",
        section_count=len(sections),
        outline_keys=len(outline) if isinstance(outline, dict) else 0,
    )
    await publish_event("draft_writing", "completed", project_id, {
        "sections": len(sections), "total_words": total_words, "mode": mode, "elapsed": elapsed,
    })
    logger.info("draft_writing.complete", sections=len(sections), words=total_words, elapsed=elapsed)

    return {
        "paper_sections": sections,
        "paper_outline": outline,
        "revision_count": revision_count + (1 if is_revision else 0),
        "hallucination_report": {} if is_revision else hallucination_report,
        "reviewer_feedback": [] if is_revision else reviewer_feedback,
        "current_agent": "draft_writing",
        "agent_history": [make_history_entry("draft_writing", mode=mode, sections=len(sections), words=total_words, elapsed=elapsed)],
        "status": "draft_complete",
    }
