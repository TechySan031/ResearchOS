"""Pydantic schemas for the Research Copilot chat endpoint.

These are intentionally kept in a separate ``schemas`` package (rather
than ``models.schemas``) because the copilot is a self-contained
feature that doesn't map to a database model.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for a copilot chat message."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question about the research project.",
    )


class ChatResponse(BaseModel):
    """Response from the copilot containing the answer and source references."""

    answer: str = Field(
        ...,
        description="The copilot's answer derived from workflow_state.",
    )
    sources: list[str] = Field(
        default_factory=list,
        description=(
            "List of workflow_state section names that were used to "
            "generate the answer (e.g. 'literature_review', 'research_gaps')."
        ),
    )
