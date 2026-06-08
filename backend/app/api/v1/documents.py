"""Document management API endpoints.

Provides endpoints for retrieving and updating document sections.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.database import DocumentSection
from app.models.schemas import DocumentSectionResponse, DocumentUpdateRequest
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=list[DocumentSectionResponse])
async def get_document_sections(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentSectionResponse]:
    """Retrieve all sections of the generated paper for a project."""
    logger.info("api.get_document_sections", project_id=project_id)
    try:
        result = await db.execute(
            select(DocumentSection)
            .where(DocumentSection.project_id == project_id)
            .order_by(DocumentSection.section_order.asc())
        )
        sections = result.scalars().all()
        return [
            DocumentSectionResponse.model_validate(s, from_attributes=True)
            for s in sections
        ]
    except Exception as exc:
        logger.error("api.get_document_sections.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch document sections: {exc}",
        ) from exc


@router.patch("/{section_id}", response_model=DocumentSectionResponse)
async def update_document_section(
    project_id: str,
    section_id: str,
    data: DocumentUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentSectionResponse:
    """Update a specific section's title, content, or order."""
    logger.info(
        "api.update_document_section",
        project_id=project_id,
        section_id=section_id,
    )
    try:
        result = await db.execute(
            select(DocumentSection)
            .where(
                DocumentSection.id == section_id,
                DocumentSection.project_id == project_id,
            )
        )
        section = result.scalar_one_or_none()
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section {section_id} not found for project {project_id}",
            )

        if data.title is not None:
            section.title = data.title
        if data.content is not None:
            section.content = data.content
            section.word_count = len(data.content.split())
        if data.section_order is not None:
            section.section_order = data.section_order

        await db.commit()
        await db.refresh(section)
        return DocumentSectionResponse.model_validate(section, from_attributes=True)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("api.update_document_section.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document section: {exc}",
        ) from exc
