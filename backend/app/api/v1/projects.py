"""Project CRUD API endpoints.

Provides REST endpoints for creating, reading, updating, and deleting
ResearchOS projects.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.dependencies import get_db
from app.models.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import ProjectService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(data: ProjectCreate) -> ProjectResponse:
    """Create a new research project.

    Args:
        data: Project creation payload with title, description, and
            user_id.

    Returns:
        The created project.
    """
    logger.info("api.create_project", title=data.title, user_id=data.user_id)

    try:
        project = await ProjectService.create_project(data)
        return ProjectResponse.model_validate(project, from_attributes=True)
    except Exception as exc:
        logger.error("api.create_project.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {exc}",
        ) from exc


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List projects",
)
async def list_projects(
    user_id: str = Query(..., description="The user ID to filter by"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
) -> list[ProjectResponse]:
    """List projects for a user with optional pagination.

    Args:
        user_id: The owner's user ID.
        skip: Pagination offset.
        limit: Pagination page size.
    """
    logger.info("api.list_projects", user_id=user_id, skip=skip, limit=limit)

    projects = await ProjectService.list_projects(
        user_id=user_id, skip=skip, limit=limit
    )
    return [
        ProjectResponse.model_validate(p, from_attributes=True)
        for p in projects
    ]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID",
)
async def get_project(project_id: str) -> ProjectResponse:
    """Retrieve a single project by its UUID.

    Args:
        project_id: The project's unique identifier.
    """
    logger.info("api.get_project", project_id=project_id)

    try:
        project = await ProjectService.get_project(project_id)
        return ProjectResponse.model_validate(project, from_attributes=True)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
) -> ProjectResponse:
    """Partially update a project's fields.

    Only fields present in the request body are updated.

    Args:
        project_id: The project's unique identifier.
        data: Fields to update.
    """
    logger.info("api.update_project", project_id=project_id)

    try:
        project = await ProjectService.update_project(project_id, data)
        return ProjectResponse.model_validate(project, from_attributes=True)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except Exception as exc:
        logger.error("api.update_project.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {exc}",
        ) from exc


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    response_class=JSONResponse,
)
async def delete_project(project_id: str):
    """Delete a project by ID.

    Args:
        project_id: The project's unique identifier.
    """
    logger.info("api.delete_project", project_id=project_id)

    try:
        await ProjectService.delete_project(project_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
