"""
ResearchOS — Agent Node Base Utilities

Shared helpers for all agent nodes.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any
import time
from app.core.events import AgentEvent, get_event_bus
from app.integrations.llm_client import LLMClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def publish_event(
    agent_name: str,
    event_type: str,
    project_id: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Publish an agent event and update the active workflow status registry."""
    try:
        bus = get_event_bus()

        await bus.publish(
            AgentEvent(
                agent_name=agent_name,
                event_type=event_type,
                project_id=project_id,
                data=data or {},
            )
        )

        # Update in-memory registry dynamically to prevent tab-switching status reset
        try:
            from app.services.research_service import _active_workflows
            if project_id in _active_workflows:
                wf = _active_workflows[project_id]
                
                # Update status on workflow events
                if event_type == "workflow_completed":
                    wf["current_agent"] = ""
                    wf["status"] = "completed"
                    wf["progress_pct"] = 100.0
                elif event_type == "workflow_failed":
                    wf["current_agent"] = ""
                    wf["status"] = "failed"
                elif event_type == "workflow_cancelled":
                    wf["current_agent"] = ""
                    wf["status"] = "cancelled"
                else:
                    # Update current agent on agent started
                    if event_type == "started":
                        wf["current_agent"] = agent_name

                    # Compute progress percentage based on agent order
                    agents_order = [
                        "research_retrieval",
                        "literature_review",
                        "citation_verification",
                        "gap_analysis",
                        "methodology_suggestion",
                        "draft_writing",
                        "hallucination_detection",
                        "formatting",
                        "journal_recommendation",
                        "reviewer_simulation",
                        "submission_preparation",
                    ]
                    if agent_name in agents_order:
                        idx = agents_order.index(agent_name)
                        if event_type == "started":
                            progress = (idx / len(agents_order)) * 100.0
                        elif event_type == "completed":
                            progress = ((idx + 1) / len(agents_order)) * 100.0
                        else:
                            progress = wf.get("progress_pct", 0.0)
                        wf["progress_pct"] = round(progress, 2)
        except Exception as e:
            logger.warning(
                "active_workflows_update_failed",
                project_id=project_id,
                error=str(e),
            )
    except Exception as exc:
        logger.warning(
            "event_publish_failed",
            agent_name=agent_name,
            event_type=event_type,
            error=str(exc),
        )


def make_history_entry(
    agent_name: str,
    status: str = "completed",
    **extra: Any,
) -> dict[str, Any]:
    """Create standard history entry."""
    entry = {
        "agent": agent_name,
        "status": status,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }

    entry.update(extra)
    return entry


def make_error_entry(
    agent_name: str,
    error: str,
) -> dict[str, Any]:
    """Create standard error entry."""
    return {
        "agent": agent_name,
        "error": error,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }


def _papers_context(
    papers: list[dict],
    max_papers: int = 25,
) -> str:
    """Convert papers into prompt context."""
    lines: list[str] = []

    for i, paper in enumerate(papers[:max_papers], start=1):
        authors = paper.get("authors")

        if isinstance(authors, list):
            if len(authors) > 5:
                author_text = ", ".join(str(a) for a in authors[:5]) + ", et al."
            else:
                author_text = ", ".join(str(a) for a in authors) if authors else "N/A"
        else:
            author_text = str(authors) if authors else "N/A"

        abstract = paper.get("abstract") or "No abstract available"
        doi = paper.get("doi") or "N/A"
        year = paper.get("year") or "N/A"

        lines.append(
            f"[REF_{i}] {paper.get('title', 'Untitled')} ({year})\n"
            f"Authors: {author_text}\n"
            f"Abstract: {abstract}\n"
            f"DOI: {doi}\n"
        )

    return "\n\n".join(lines)


async def stream_llm_to_event_bus(
    agent_name: str,
    project_id: str,
    section: str,
    llm: LLMClient,
    provider: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """
    Stream LLM output through EventBus and return complete text.
    """

    chunks: list[str] = []
    start_ns = time.monotonic_ns()
    first_token_seen = False

    try:
        async for token in llm.stream(
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            if not first_token_seen:
                ttft_ms = (
                    time.monotonic_ns() -start_ns
                )/ 1_000_000    
                first_token_seen = True

                await publish_event(
                    agent_name=agent_name,
                    event_type="metric_recorded",
                    project_id=project_id,
                    data={
                        "metric_type": "ttft_ms",
                        "value":round(ttft_ms,2),
                        "section":section,
                    },
                )
            chunks.append(token)

            await publish_event(
                agent_name=agent_name,
                event_type="stream_token",
                project_id=project_id,
                data={
                    "token": token,
                    "section": section,
                },
            )

        return "".join(chunks)

    except Exception as exc:
        logger.warning(
            "stream_fallback",
            agent_name=agent_name,
            error=str(exc),
        )

        return await llm.generate(
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
