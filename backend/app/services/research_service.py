"""Research workflow orchestration service.

Manages the lifecycle of a LangGraph research workflow:
start, pause, resume, cancel, and status queries.
"""

from __future__ import annotations

import asyncio
import uuid
import datetime as _dt
from typing import Any

from app.agents.graph import build_research_graph, run_workflow
from app.core.events import EventBus, AgentEvent
from app.core.exceptions import NotFoundError, WorkflowError
from app.models.database import Project, get_async_session
from app.models.schemas import ResearchStartRequest, ResearchStatusResponse
from app.services.project_service import ProjectService
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ── In-memory workflow registry ────────────────────────────────────────
# Maps project_id → workflow metadata.  In production, replace with
# Redis or a proper task queue (Celery, ARQ, etc.).

_active_workflows: dict[str, dict[str, Any]] = {}


class ResearchService:
    """Orchestrates the multi-agent research workflow lifecycle."""

    # ── START ───────────────────────────────────────────────────────

    @staticmethod
    async def start_research(
        project_id: str,
        request: ResearchStartRequest,
    ) -> str:
        """Launch a new research workflow as a background task.

        Args:
            project_id: UUID of the owning project.
            request: The research start request payload containing topic
                and optional preferences.

        Returns:
            A unique ``workflow_id`` string.

        Raises:
            NotFoundError: If the project does not exist.
            WorkflowError: If a workflow is already running for this project.
        """
        # Validate project exists
        project = await ProjectService.get_project(project_id)

        # Prevent duplicate workflows
        if project_id in _active_workflows:
            existing = _active_workflows[project_id]
            if existing.get("status") in ("running", "paused"):
                raise WorkflowError(
                    f"A workflow is already {existing['status']} for project "
                    f"{project_id}. Cancel it first."
                )

        workflow_id = str(uuid.uuid4())

        # Register the workflow
        _active_workflows[project_id] = {
            "workflow_id": workflow_id,
            "project_id": project_id,
            "topic": project.topic or "",
            "status": "running",
            "started_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "task": None,
            "cancel_event": asyncio.Event(),
        }

        # Update project status
        async with get_async_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            proj = result.scalar_one_or_none()
            if proj is not None:
                proj.status = "researching"
                proj.updated_at = _dt.datetime.now(_dt.timezone.utc)
                await session.commit()

        # Publish start event
        try:
            bus = EventBus()
            await bus.publish(
                AgentEvent(
                    agent_name="system",
                    event_type="workflow_started",
                    project_id=project_id,
                    data={
                        "workflow_id": workflow_id,
                        "topic": project.topic or "",
                    },
                )
            )
        except Exception:
            logger.warning("research_service.event_publish_failed")

        # Launch as background task
        task = asyncio.create_task(
            _run_workflow_task(
                workflow_id=workflow_id,
                project_id=project_id,
                topic=project.topic or "",
                user_preferences=getattr(request, "user_preferences", None) or {},
                max_revisions=getattr(request, "max_revisions", 3),
                format_style=getattr(request, "format_style", "ieee"),
            )
        )
        _active_workflows[project_id]["task"] = task

        logger.info(
            "research_service.started",
            project_id=project_id,
            workflow_id=workflow_id,
            topic=project.topic or "",
        )
        return workflow_id

    # ── STATUS ──────────────────────────────────────────────────────

    @staticmethod
    async def get_research_status(project_id: str) -> ResearchStatusResponse:
        """Get the current status of a project's research workflow.

        Args:
            project_id: UUID of the project.

        Returns:
            A ``ResearchStatusResponse`` with current state information.

        Raises:
            NotFoundError: If no workflow has been started for this project.
        """
        if project_id not in _active_workflows:
            raise NotFoundError(
                f"No active workflow found for project {project_id}"
            )

        wf = _active_workflows[project_id]
        return ResearchStatusResponse(
            workflow_id=wf["workflow_id"],
            project_id=project_id,
            topic=wf.get("topic", ""),
            status=wf.get("status", "unknown"),
            started_at=wf.get("started_at", ""),
            current_agent=wf.get("current_agent", ""),
            completed_at=wf.get("completed_at"),
            error=wf.get("error"),
        )

    # ── PAUSE ───────────────────────────────────────────────────────

    @staticmethod
    async def pause_research(project_id: str) -> None:
        """Pause a running research workflow.

        The current node will finish execution, but no new nodes will be
        dispatched until ``resume_research`` is called.

        Args:
            project_id: UUID of the project.

        Raises:
            NotFoundError: If no workflow is active.
            WorkflowError: If the workflow is not in a pausable state.
        """
        if project_id not in _active_workflows:
            raise NotFoundError(
                f"No active workflow for project {project_id}"
            )

        wf = _active_workflows[project_id]
        if wf["status"] != "running":
            raise WorkflowError(
                f"Cannot pause workflow in state '{wf['status']}'"
            )

        wf["status"] = "paused"

        try:
            bus = EventBus()
            await bus.publish(
                AgentEvent(
                    agent_name="system",
                    event_type="workflow_paused",
                    project_id=project_id,
                    data={"workflow_id": wf["workflow_id"]},
                )
            )
        except Exception:
            pass

        logger.info(
            "research_service.paused",
            project_id=project_id,
            workflow_id=wf["workflow_id"],
        )

    # ── RESUME ──────────────────────────────────────────────────────

    @staticmethod
    async def resume_research(project_id: str) -> None:
        """Resume a paused research workflow.

        Args:
            project_id: UUID of the project.

        Raises:
            NotFoundError: If no workflow is active.
            WorkflowError: If the workflow is not paused.
        """
        if project_id not in _active_workflows:
            raise NotFoundError(
                f"No active workflow for project {project_id}"
            )

        wf = _active_workflows[project_id]
        if wf["status"] != "paused":
            raise WorkflowError(
                f"Cannot resume workflow in state '{wf['status']}'"
            )

        wf["status"] = "running"

        try:
            bus = EventBus()
            await bus.publish(
                AgentEvent(
                    agent_name="system",
                    event_type="workflow_resumed",
                    project_id=project_id,
                    data={"workflow_id": wf["workflow_id"]},
                )
            )
        except Exception:
            pass

        logger.info(
            "research_service.resumed",
            project_id=project_id,
            workflow_id=wf["workflow_id"],
        )

    # ── CANCEL ──────────────────────────────────────────────────────

    @staticmethod
    async def cancel_research(project_id: str) -> None:
        """Cancel a running or paused research workflow.

        Args:
            project_id: UUID of the project.

        Raises:
            NotFoundError: If no workflow is active.
            WorkflowError: If the workflow has already completed.
        """
        if project_id not in _active_workflows:
            raise NotFoundError(
                f"No active workflow for project {project_id}"
            )

        wf = _active_workflows[project_id]
        if wf["status"] in ("completed", "failed"):
            raise WorkflowError(
                f"Workflow already in terminal state '{wf['status']}'"
            )

        # Signal cancellation
        cancel_event: asyncio.Event | None = wf.get("cancel_event")
        if cancel_event:
            cancel_event.set()

        # Cancel the asyncio Task if running
        task: asyncio.Task | None = wf.get("task")
        if task and not task.done():
            task.cancel()

        wf["status"] = "cancelled"
        wf["completed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()

        # Update project status
        async with get_async_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            proj = result.scalar_one_or_none()
            if proj is not None:
                proj.status = "cancelled"
                proj.updated_at = _dt.datetime.now(_dt.timezone.utc)
                await session.commit()

        try:
            bus = EventBus()
            await bus.publish(
                AgentEvent(
                    agent_name="system",
                    event_type="workflow_cancelled",
                    project_id=project_id,
                    data={"workflow_id": wf["workflow_id"]},
                )
            )
        except Exception:
            pass

        logger.info(
            "research_service.cancelled",
            project_id=project_id,
            workflow_id=wf["workflow_id"],
        )


# ── Background task ────────────────────────────────────────────────────


async def _run_workflow_task(
    *,
    workflow_id: str,
    project_id: str,
    topic: str,
    user_preferences: dict[str, Any],
    max_revisions: int,
    format_style: str,
) -> None:
    """Run the LangGraph workflow inside a background asyncio task.

    Updates the in-memory workflow registry with status transitions and
    persists the final project status to the database.
    """
    try:
        logger.info(
            "research_service.task_started",
            workflow_id=workflow_id,
            project_id=project_id,
        )

        final_state = await run_workflow(
            topic=topic,
            project_id=project_id,
            user_preferences=user_preferences,
            max_revisions=max_revisions,
            format_style=format_style,
        )

        # Update workflow metadata
        if project_id in _active_workflows:
            wf = _active_workflows[project_id]
            wf["status"] = "completed"
            wf["completed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
            wf["current_agent"] = final_state.get("current_agent", "")

        # Update project status
        async with get_async_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            proj = result.scalar_one_or_none()
            if proj is not None:
                proj.status = "completed"
                proj.updated_at = _dt.datetime.now(_dt.timezone.utc)
                await session.commit()

        try:
            bus = EventBus()
            await bus.publish(
                AgentEvent(
                    agent_name="system",
                    event_type="workflow_completed",
                    project_id=project_id,
                    data={"workflow_id": workflow_id},
                )
            )
        except Exception:
            pass

        logger.info(
            "research_service.task_completed",
            workflow_id=workflow_id,
            project_id=project_id,
        )

    except asyncio.CancelledError:
        logger.warning(
            "research_service.task_cancelled",
            workflow_id=workflow_id,
            project_id=project_id,
        )

    except Exception as exc:
        logger.error(
            "research_service.task_failed",
            workflow_id=workflow_id,
            project_id=project_id,
            error=str(exc),
        )

        if project_id in _active_workflows:
            wf = _active_workflows[project_id]
            wf["status"] = "failed"
            wf["error"] = str(exc)
            wf["completed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()

        # Update project status
        try:
            async with get_async_session() as session:
                from sqlalchemy import select

                result = await session.execute(
                    select(Project).where(Project.id == project_id)
                )
                proj = result.scalar_one_or_none()
                if proj is not None:
                    proj.status = "failed"
                    proj.updated_at = _dt.datetime.now(_dt.timezone.utc)
                    await session.commit()
        except Exception:
            pass

        try:
            bus = EventBus()
            await bus.publish(
                AgentEvent(
                    agent_name="system",
                    event_type="workflow_failed",
                    project_id=project_id,
                    data={
                        "workflow_id": workflow_id,
                        "error": str(exc),
                    },
                )
            )
        except Exception:
            pass
