"""Paper management API endpoints.

Provides endpoints for searching, listing, and retrieving papers
associated with a research project.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status, UploadFile, File

from app.core.exceptions import NotFoundError
from app.models.schemas import PaperSearchRequest, PaperResponse, PaperUploadResponse
from app.rag.ingestion import PaperIngestor
from app.services.paper_service import PaperService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["papers"],
)


@router.post(
    "/search",
    response_model=list[PaperResponse],
    summary="Search for papers",
)
async def search_papers(
    project_id: str,
    request: PaperSearchRequest,
) -> list[PaperResponse]:
    """Search external academic databases for papers.

    Results are returned but **not** automatically persisted.  Use the
    retrieval pipeline or a follow-up save call to persist.

    Args:
        project_id: UUID of the owning project.
        request: Search parameters (query, sources, max_results).
    """
    logger.info(
        "api.search_papers",
        project_id=project_id,
        query=request.query,
    )

    try:
        papers = await PaperService.search_papers(
            project_id=project_id,
            query=request.query,
            sources=getattr(request, "sources", None),
        )

        return [
            PaperResponse.model_validate(p, from_attributes=True)
            if hasattr(p, "__dict__") and hasattr(p, "id")
            else PaperResponse(
                id=p.get("id", ""),
                title=p.get("title", ""),
                authors=p.get("authors", []),
                abstract=p.get("abstract", ""),
                year=p.get("year"),
                doi=p.get("doi"),
                source=p.get("source", "unknown"),
                citation_count=p.get("citation_count", 0),
                url=p.get("url", ""),
            )
            for p in papers
        ]
    except Exception as exc:
        logger.error("api.search_papers.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paper search failed: {exc}",
        ) from exc


@router.get(
    "",
    response_model=list[PaperResponse],
    summary="List papers for a project",
)
async def list_papers(
    project_id: str,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
) -> list[PaperResponse]:
    """List papers stored for a specific project.

    Args:
        project_id: UUID of the owning project.
        skip: Pagination offset.
        limit: Maximum records to return.
    """
    logger.info(
        "api.list_papers",
        project_id=project_id,
        skip=skip,
        limit=limit,
    )

    papers = await PaperService.list_papers(
        project_id=project_id,
        skip=skip,
        limit=limit,
    )

    return [
        PaperResponse.model_validate(p, from_attributes=True)
        for p in papers
    ]


@router.get(
    "/{paper_id}",
    response_model=PaperResponse,
    summary="Get a paper by ID",
)
async def get_paper(
    project_id: str,
    paper_id: str,
) -> PaperResponse:
    """Retrieve a single paper by its UUID.

    Args:
        project_id: UUID of the owning project (used for route nesting).
        paper_id: UUID of the paper.
    """
    logger.info(
        "api.get_paper",
        project_id=project_id,
        paper_id=paper_id,
    )

    try:
        paper = await PaperService.get_paper(paper_id)
        return PaperResponse.model_validate(paper, from_attributes=True)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper {paper_id} not found",
        )


@router.post(
    "/upload",
    response_model=PaperUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF paper",
)
async def upload_paper(
    project_id: str,
    file: UploadFile = File(...),
) -> PaperUploadResponse:
    """Upload an academic paper PDF, extract text/metadata, and index it for RAG.

    Args:
        project_id: UUID of the project.
        file: Multipart uploaded PDF file.
    """
    logger.info(
        "api.upload_paper",
        project_id=project_id,
        filename=file.filename,
    )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    # Save to a temporary file
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / file.filename

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ingest paper
        ingestor = PaperIngestor()
        ingested = await ingestor.ingest_from_pdf(temp_path)

        # Get pages count
        pages_count = 1
        try:
            import fitz
            doc = fitz.open(temp_path)
            pages_count = len(doc)
            doc.close()
        except Exception:
            pass

        abstract = ingested.sections.get("abstract", "")
        if not abstract and ingested.text:
            abstract = ingested.text[:1000]

        paper_dict = {
            "title": ingested.metadata.get("title") or file.filename,
            "authors": ingested.metadata.get("authors") or [],
            "abstract": abstract,
            "year": ingested.metadata.get("year"),
            "doi": ingested.metadata.get("doi"),
            "source": "upload",
            "citation_count": 0,
            "url": f"file:///{temp_path.as_posix()}",
        }

        # Save to database
        saved_papers = await PaperService.save_papers(project_id, [paper_dict])
        if not saved_papers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paper already uploaded or duplicate title/DOI.",
            )

        saved_paper = saved_papers[0]

        return PaperUploadResponse(
            id=saved_paper.id,
            title=saved_paper.title,
            filename=file.filename,
            pages=pages_count,
            message="Paper uploaded and processed successfully.",
        )

    except Exception as exc:
        logger.error("api.upload_paper.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process uploaded PDF: {exc}",
        ) from exc
    finally:
        # Clean up temporary file
        try:
            if temp_path.exists():
                os.remove(temp_path)
            os.rmdir(temp_dir)
        except Exception:
            pass
