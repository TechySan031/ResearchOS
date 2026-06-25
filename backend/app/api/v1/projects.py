"""Project CRUD API endpoints.

Provides REST endpoints for creating, reading, updating, and deleting
ResearchOS projects.  All endpoints require authentication and scope
project queries to the current user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser, get_current_user, require_researcher
from app.dependencies import get_db
from app.models.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.audit_service import AuditService
from app.services.project_service import ProjectService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["projects"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    data: ProjectCreate,
    request: Request,
    user: CurrentUser = Depends(require_researcher),
) -> ProjectResponse:
    """Create a new research project.

    Args:
        data: Project creation payload with title, description, and topic.
        request: The incoming request.
        user: The authenticated user.

    Returns:
        The created project.
    """
    logger.info("api.create_project", title=data.title, user_id=user.id)

    try:
        # Override user_id with authenticated user
        data.user_id = user.id
        project = await ProjectService.create_project(data)

        await AuditService.log(
            action="project_created",
            user_id=user.id,
            resource_type="project",
            resource_id=project.id,
            detail=f"Created project: {project.title}",
            ip_address=_client_ip(request),
        )

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
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    user: CurrentUser = Depends(get_current_user),
) -> list[ProjectResponse]:
    """List projects for the authenticated user with optional pagination.

    Args:
        skip: Pagination offset.
        limit: Pagination page size.
        user: The authenticated user.
    """
    logger.info("api.list_projects", user_id=user.id, skip=skip, limit=limit)

    projects = await ProjectService.list_projects(
        user_id=user.id, skip=skip, limit=limit
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
async def get_project(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> ProjectResponse:
    """Retrieve a single project by its UUID.

    Args:
        project_id: The project's unique identifier.
        user: The authenticated user.
    """
    logger.info("api.get_project", project_id=project_id)

    try:
        project = await ProjectService.get_project(project_id)
        # Verify ownership (admins can see all)
        if project.owner_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this project",
            )
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
    request: Request,
    user: CurrentUser = Depends(require_researcher),
) -> ProjectResponse:
    """Partially update a project's fields.

    Only fields present in the request body are updated.

    Args:
        project_id: The project's unique identifier.
        data: Fields to update.
        request: The incoming request.
        user: The authenticated user.
    """
    logger.info("api.update_project", project_id=project_id)

    try:
        # Verify ownership first
        existing = await ProjectService.get_project(project_id)
        if existing.owner_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this project",
            )

        project = await ProjectService.update_project(project_id, data)

        await AuditService.log(
            action="project_updated",
            user_id=user.id,
            resource_type="project",
            resource_id=project_id,
            ip_address=_client_ip(request),
        )

        return ProjectResponse.model_validate(project, from_attributes=True)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except HTTPException:
        raise
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
async def delete_project(
    project_id: str,
    request: Request,
    user: CurrentUser = Depends(require_researcher),
):
    """Delete a project by ID.

    Args:
        project_id: The project's unique identifier.
        request: The incoming request.
        user: The authenticated user.
    """
    logger.info("api.delete_project", project_id=project_id)

    try:
        # Verify ownership first
        existing = await ProjectService.get_project(project_id)
        if existing.owner_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this project",
            )

        await ProjectService.delete_project(project_id)

        await AuditService.log(
            action="project_deleted",
            user_id=user.id,
            resource_type="project",
            resource_id=project_id,
            ip_address=_client_ip(request),
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except HTTPException:
        raise
