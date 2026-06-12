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
    """Publish an agent event."""
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
        authors = paper.get("authors", [])

        if isinstance(authors, list):
            author_text = ", ".join(str(a) for a in authors[:5])
        else:
            author_text = str(authors)

        lines.append(
            f"[REF_{i}] {paper.get('title', 'Untitled')}\n"
            f"Authors: {author_text}\n"
            f"Abstract: {paper.get('abstract', '')}\n"
            f"DOI: {paper.get('doi', '')}\n"
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
