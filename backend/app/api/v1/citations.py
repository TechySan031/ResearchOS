"""Citation management API endpoints.

Provides endpoints for retrieving and managing citations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.database import Citation
from app.models.schemas import CitationResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=list[CitationResponse])
async def get_citations(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[CitationResponse]:
    """Retrieve all citations generated for a project."""
    logger.info("api.get_citations", project_id=project_id)
    try:
        result = await db.execute(
            select(Citation)
            .where(Citation.project_id == project_id)
            .order_by(Citation.created_at.desc())
        )
        citations = result.scalars().all()
        return [
            CitationResponse.model_validate(c, from_attributes=True)
            for c in citations
        ]
    except Exception as exc:
        logger.error("api.get_citations.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch citations: {exc}",
        ) from exc
