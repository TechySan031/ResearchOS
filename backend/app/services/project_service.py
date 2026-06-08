"""Project CRUD service.

Encapsulates all database operations related to ``Project`` entities.
Every public method acquires its own async session (via the session
factory) so that callers don't need to manage transactions.
"""

from __future__ import annotations

import uuid
import datetime as _dt
from typing import Sequence

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.database import Project, get_async_session
from app.models.schemas import ProjectCreate, ProjectUpdate
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ProjectService:
    """Service class for Project CRUD operations.

    All methods are async and manage their own database sessions via
    ``get_async_session()``.
    """

    # ── CREATE ──────────────────────────────────────────────────────

    @staticmethod
    async def create_project(data: ProjectCreate) -> Project:
        """Create a new project.

        Args:
            data: Validated project creation payload.

        Returns:
            The newly created ``Project`` ORM instance.
        """
        async with get_async_session() as session:
            project = Project(
                id=str(uuid.uuid4()),
                title=data.title,
                description=data.description or "",
                owner_id=data.user_id,
                status="created",
                created_at=_dt.datetime.now(_dt.timezone.utc),
                updated_at=_dt.datetime.now(_dt.timezone.utc),
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)

            logger.info(
                "project.created",
                project_id=project.id,
                title=project.title,
                owner_id=project.owner_id,
            )
            return project

    # ── READ ────────────────────────────────────────────────────────

    @staticmethod
    async def get_project(project_id: str) -> Project:
        """Retrieve a single project by ID.

        Args:
            project_id: UUID of the project.

        Returns:
            The matching ``Project``.

        Raises:
            NotFoundError: If no project with the given ID exists.
        """
        async with get_async_session() as session:
            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")
            return project

    @staticmethod
    async def list_projects(
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Project]:
        """List projects for a given user with pagination.

        Args:
            user_id: The owning user's ID.
            skip: Number of rows to skip (offset).
            limit: Maximum number of rows to return.

        Returns:
            A list of ``Project`` instances.
        """
        async with get_async_session() as session:
            stmt = (
                select(Project)
                .where(Project.owner_id == user_id)
                .order_by(Project.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # ── UPDATE ──────────────────────────────────────────────────────

    @staticmethod
    async def update_project(
        project_id: str,
        data: ProjectUpdate,
    ) -> Project:
        """Partially update a project.

        Only fields explicitly set in ``data`` are written.

        Args:
            project_id: UUID of the project to update.
            data: Validated update payload.

        Returns:
            The updated ``Project``.

        Raises:
            NotFoundError: If the project does not exist.
        """
        async with get_async_session() as session:
            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(project, field, value)

            project.updated_at = _dt.datetime.now(_dt.timezone.utc)
            await session.commit()
            await session.refresh(project)

            logger.info(
                "project.updated",
                project_id=project_id,
                updated_fields=list(update_data.keys()),
            )
            return project

    # ── DELETE ──────────────────────────────────────────────────────

    @staticmethod
    async def delete_project(project_id: str) -> None:
        """Soft- or hard-delete a project.

        Currently performs a hard delete.  Switch to a ``deleted_at``
        timestamp if soft-delete semantics are required.

        Args:
            project_id: UUID of the project to delete.

        Raises:
            NotFoundError: If the project does not exist.
        """
        async with get_async_session() as session:
            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")

            await session.delete(project)
            await session.commit()

            logger.info("project.deleted", project_id=project_id)
