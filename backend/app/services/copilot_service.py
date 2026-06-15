"""Research Copilot service.

Provides conversational Q&A over a project's workflow_state using the
existing Mistral LLM integration.  No external data sources are used —
all context comes from the persisted workflow results.
"""

from __future__ import annotations

import json
from typing import Any

import tiktoken

from app.agents.prompts.copilot import COPILOT_SYSTEM_PROMPT
from app.core.exceptions import NotFoundError, ExternalAPIError
from app.integrations.llm_client import LLMClient
from app.schemas.copilot import ChatResponse
from app.services.project_service import ProjectService
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Maximum context tokens to send to the LLM (prompt + context).
# Mistral-large supports 32k; we cap at 12k for the context portion
# to leave room for the system prompt (~500 tokens) and the response.
_MAX_CONTEXT_TOKENS = 12_000

# Workflow sections to include in context, ordered by relevance.
# Each entry is (section_key, human_label, max_chars).
_CONTEXT_SECTIONS: list[tuple[str, str, int]] = [
    ("literature_review",           "Literature Review",           6000),
    ("key_themes",                  "Key Themes",                  1000),
    ("research_gaps",               "Research Gaps",               3000),
    ("suggested_methodologies",     "Suggested Methodologies",     3000),
    ("selected_methodology",        "Selected Methodology",        2000),
    ("retrieved_papers",            "Retrieved Papers",            5000),
    ("paper_sections",              "Paper Draft Sections",        5000),
    ("hallucination_report",        "Hallucination Report",        2000),
    ("journal_recommendations",     "Journal Recommendations",     2000),
    ("reviewer_feedback",           "Reviewer Feedback",           3000),
    ("formatted_paper",             "Formatted Paper",             4000),
    ("submission_package",          "Submission Package",          2000),
]

# tiktoken encoding for token counting (cl100k_base works for Mistral)
try:
    _encoding = tiktoken.get_encoding("cl100k_base")
except Exception:
    _encoding = None


def _count_tokens(text: str) -> int:
    """Count tokens in a string using tiktoken, fallback to word estimate."""
    if _encoding is not None:
        return len(_encoding.encode(text))
    # Rough fallback: ~4 chars per token
    return len(text) // 4


class ResearchCopilotService:
    """Chat service that answers questions using project workflow_state."""

    @staticmethod
    async def chat(project_id: str, message: str) -> ChatResponse:
        """Process a user chat message and return an answer.

        Args:
            project_id: UUID of the project.
            message: The user's question.

        Returns:
            A ``ChatResponse`` with the answer and source section names.

        Raises:
            NotFoundError: If the project doesn't exist or has no workflow_state.
            ExternalAPIError: If the LLM call fails.
        """
        logger.info(
            "copilot.chat.start",
            project_id=project_id,
            message_length=len(message),
        )

        # 1. Load project and workflow_state
        project = await ProjectService.get_project(project_id)
        workflow_state = project.workflow_state

        if not workflow_state or not isinstance(workflow_state, dict):
            raise NotFoundError(
                "This project has no workflow results yet. "
                "Run the research workflow first."
            )

        # 2. Build structured context from workflow_state
        context, included_sections = _build_context(workflow_state)

        if not context.strip():
            raise NotFoundError(
                "The workflow completed but produced no usable content. "
                "Try running the workflow again."
            )

        context_tokens = _count_tokens(context)
        logger.info(
            "copilot.context_built",
            project_id=project_id,
            sections=included_sections,
            context_tokens=context_tokens,
        )

        # 3. Build the user prompt with context
        user_prompt = (
            f"## Project Context\n\n{context}\n\n"
            f"---\n\n"
            f"## User Question\n\n{message}"
        )

        # 4. Call Mistral via existing LLMClient
        try:
            llm = LLMClient()
            answer = await llm.generate(
                provider="mistral",
                system_prompt=COPILOT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=2048,
            )
        except Exception as exc:
            logger.error(
                "copilot.llm_error",
                project_id=project_id,
                error=str(exc),
            )
            raise ExternalAPIError(
                f"Failed to generate copilot response: {exc}",
                service="mistral",
            ) from exc

        # 5. Detect which sections were referenced in the answer
        sources = _extract_sources(answer, included_sections)

        logger.info(
            "copilot.chat.complete",
            project_id=project_id,
            answer_length=len(answer),
            sources=sources,
        )

        return ChatResponse(answer=answer, sources=sources)


# ── Context Builder ────────────────────────────────────────────────────


def _build_context(
    workflow_state: dict[str, Any],
) -> tuple[str, list[str]]:
    """Build a structured text context from workflow_state.

    Assembles sections in priority order, truncating each to its
    configured max_chars and stopping when the total token budget
    is reached.

    Returns:
        A tuple of (context_text, list_of_included_section_keys).
    """
    parts: list[str] = []
    included: list[str] = []
    total_tokens = 0

    for section_key, label, max_chars in _CONTEXT_SECTIONS:
        value = workflow_state.get(section_key)
        if value is None:
            continue

        # Format the value
        section_text = _format_section_value(value, max_chars)
        if not section_text.strip():
            continue

        # Build the section block
        block = f"### {label}\n\n{section_text}\n"

        # Check token budget
        block_tokens = _count_tokens(block)
        if total_tokens + block_tokens > _MAX_CONTEXT_TOKENS:
            # Try to fit a truncated version
            remaining_tokens = _MAX_CONTEXT_TOKENS - total_tokens
            if remaining_tokens > 200:
                # Rough truncation by characters
                max_remaining_chars = remaining_tokens * 4
                truncated = section_text[:max_remaining_chars] + "\n[... truncated]"
                block = f"### {label}\n\n{truncated}\n"
                parts.append(block)
                included.append(section_key)
            break

        parts.append(block)
        included.append(section_key)
        total_tokens += block_tokens

    return "\n".join(parts), included


def _format_section_value(value: Any, max_chars: int) -> str:
    """Format a workflow_state value as readable text, truncated to max_chars."""
    if isinstance(value, str):
        text = value
    elif isinstance(value, list):
        if len(value) == 0:
            return ""
        # Format list items
        items: list[str] = []
        for item in value:
            if isinstance(item, str):
                items.append(f"- {item}")
            elif isinstance(item, dict):
                # For papers, gaps, etc. — format key fields
                formatted = _format_dict_item(item)
                items.append(formatted)
            else:
                items.append(f"- {str(item)}")
        text = "\n".join(items)
    elif isinstance(value, dict):
        if len(value) == 0:
            return ""
        # For paper_sections, format as sub-sections
        items = []
        for k, v in value.items():
            label = k.replace("_", " ").title()
            content = str(v)[:1500] if isinstance(v, str) else json.dumps(v, indent=2)[:1500]
            items.append(f"**{label}:**\n{content}")
        text = "\n\n".join(items)
    elif isinstance(value, bool):
        text = "Yes" if value else "No"
    else:
        text = str(value)

    # Truncate
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[... truncated]"

    return text


def _format_dict_item(item: dict[str, Any]) -> str:
    """Format a dict (paper, gap, methodology, etc.) as a bullet item."""
    # Try common field patterns
    title = item.get("title") or item.get("name") or ""
    parts = [f"- **{title}**"] if title else ["- "]

    for field in ("authors", "year", "source", "doi", "description",
                  "importance", "score", "reason", "feedback", "comments"):
        val = item.get(field)
        if val is not None:
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val[:5])
            parts.append(f"  {field}: {val}")

    # If nothing matched, dump the first few keys
    if len(parts) == 1 and not title:
        summary = json.dumps(item, default=str)[:300]
        parts = [f"- {summary}"]

    return "\n".join(parts)


# ── Source Extraction ──────────────────────────────────────────────────

# Mapping of section keys to phrases that indicate they were referenced
_SECTION_KEYWORDS: dict[str, list[str]] = {
    "literature_review":       ["literature review", "literature", "review of"],
    "key_themes":              ["theme", "key theme"],
    "research_gaps":           ["research gap", "gap analysis", "gaps identified", "gaps found"],
    "suggested_methodologies": ["methodolog", "method", "approach"],
    "selected_methodology":    ["selected methodolog", "chosen method", "selected approach"],
    "retrieved_papers":        ["paper", "retrieved paper", "study", "studies"],
    "paper_sections":          ["draft", "section", "paper section"],
    "hallucination_report":    ["hallucination", "verification", "fact-check"],
    "journal_recommendations": ["journal", "venue", "publication"],
    "reviewer_feedback":       ["reviewer", "peer review", "feedback", "weakness"],
    "formatted_paper":         ["formatted paper", "final paper", "formatted"],
    "submission_package":      ["submission", "cover letter", "checklist"],
}


def _extract_sources(answer: str, included_sections: list[str]) -> list[str]:
    """Identify which workflow sections were referenced in the answer."""
    answer_lower = answer.lower()
    sources: list[str] = []

    for section_key in included_sections:
        keywords = _SECTION_KEYWORDS.get(section_key, [])
        if any(kw in answer_lower for kw in keywords):
            sources.append(section_key)

    # If no explicit references detected, include the first section
    # (the most relevant one, since they're priority-ordered)
    if not sources and included_sections:
        sources.append(included_sections[0])

    return sources
