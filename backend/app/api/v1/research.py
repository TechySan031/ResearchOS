"""
ResearchOS — Research Workflow API Endpoints

Endpoints for starting, monitoring, pausing, resuming, and cancelling
multi-agent research workflows.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.research_service import ResearchService
from app.models.schemas import (
    ResearchStartRequest,
    ResearchStatusResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/start", response_model=ResearchStatusResponse)
async def start_research(
    project_id: str,
    request: ResearchStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a multi-agent research workflow for a project.

    This launches the LangGraph supervisor workflow as a background task.
    The workflow executes all agents sequentially (retrieval → review →
    gaps → methodology → drafting → verification → formatting → submission).

    Use the WebSocket endpoint or GET /status to monitor progress.
    """
    try:
        workflow_id = await ResearchService.start_research(
            project_id=project_id,
            request=request,
        )
        logger.info(
            "research_workflow_started",
            project_id=project_id,
            workflow_id=workflow_id,
        )
        return await ResearchService.get_research_status(project_id)
    except Exception as e:
        logger.error(
            "research_start_failed",
            project_id=project_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to start research: {e}")


@router.get("/status", response_model=ResearchStatusResponse)
async def get_research_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current status of a research workflow.

    Returns the current agent, overall progress, agent history,
    and any errors encountered.
    """
    try:
        return await ResearchService.get_research_status(project_id)
    except Exception as e:
        logger.error(
            "research_status_fetch_failed",
            project_id=project_id,
            error=str(e),
        )
        raise HTTPException(status_code=404, detail=f"Research status not found: {e}")


@router.post("/pause")
async def pause_research(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Pause a running research workflow.

    The workflow can be resumed later from the last checkpoint.
    Currently in-progress agent tasks will complete before pausing.
    """
    try:
        await ResearchService.pause_research(project_id)
        logger.info("research_workflow_paused", project_id=project_id)
        return {"status": "paused", "project_id": project_id}
    except Exception as e:
        logger.error(
            "research_pause_failed",
            project_id=project_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=f"Failed to pause: {e}")


@router.post("/resume")
async def resume_research(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Resume a paused research workflow from the last checkpoint.
    """
    try:
        await ResearchService.resume_research(project_id)
        logger.info("research_workflow_resumed", project_id=project_id)
        return {"status": "resumed", "project_id": project_id}
    except Exception as e:
        logger.error(
            "research_resume_failed",
            project_id=project_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=f"Failed to resume: {e}")


@router.post("/cancel")
async def cancel_research(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a running or paused research workflow.

    This is irreversible. All intermediate results are preserved
    but the workflow cannot be resumed.
    """
    try:
        await ResearchService.cancel_research(project_id)
        logger.info("research_workflow_cancelled", project_id=project_id)
        return {"status": "cancelled", "project_id": project_id}
    except Exception as e:
        logger.error(
            "research_cancel_failed",
            project_id=project_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=f"Failed to cancel: {e}")
