"""Research Copilot API endpoint.

Provides a chat endpoint that answers user questions about their
research project using the project's persisted workflow_state.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import NotFoundError, ExternalAPIError
from app.schemas.copilot import ChatRequest, ChatResponse
from app.services.copilot_service import ResearchCopilotService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["copilot"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with the Research Copilot",
    description=(
        "Send a question about the research project and receive an "
        "answer grounded in the project's workflow results."
    ),
)
async def chat(
    project_id: str,
    body: ChatRequest,
) -> ChatResponse:
    """Process a copilot chat message.

    Args:
        project_id: UUID of the project (from URL path).
        body: Chat request containing the user's message.

    Returns:
        ChatResponse with the answer and source references.
    """
    logger.info(
        "api.copilot.chat",
        project_id=project_id,
        message_length=len(body.message),
    )

    try:
        return await ResearchCopilotService.chat(project_id, body.message)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ExternalAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "api.copilot.chat.error",
            project_id=project_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Copilot error: {exc}",
        ) from exc
