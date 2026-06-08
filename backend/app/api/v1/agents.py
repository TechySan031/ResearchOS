"""Agent status and logging API endpoints.

Provides endpoints for retrieving agent execution logs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.database import AgentLog
from app.models.schemas import AgentLogResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/logs", response_model=list[AgentLogResponse])
async def get_all_logs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[AgentLogResponse]:
    """Retrieve all agent logs for a specific project."""
    logger.info("api.get_all_logs", project_id=project_id)
    try:
        result = await db.execute(
            select(AgentLog)
            .where(AgentLog.project_id == project_id)
            .order_by(AgentLog.created_at.asc())
        )
        logs = result.scalars().all()
        return [
            AgentLogResponse.model_validate(l, from_attributes=True)
            for l in logs
        ]
    except Exception as exc:
        logger.error("api.get_all_logs.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agent logs: {exc}",
        ) from exc


@router.get("/{agent_name}/logs", response_model=list[AgentLogResponse])
async def get_agent_logs(
    project_id: str,
    agent_name: str,
    db: AsyncSession = Depends(get_db),
) -> list[AgentLogResponse]:
    """Retrieve agent logs for a specific agent in a project."""
    logger.info(
        "api.get_agent_logs",
        project_id=project_id,
        agent_name=agent_name,
    )
    try:
        result = await db.execute(
            select(AgentLog)
            .where(
                AgentLog.project_id == project_id,
                AgentLog.agent_name == agent_name,
            )
            .order_by(AgentLog.created_at.asc())
        )
        logs = result.scalars().all()
        return [
            AgentLogResponse.model_validate(l, from_attributes=True)
            for l in logs
        ]
    except Exception as exc:
        logger.error("api.get_agent_logs.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch logs for agent {agent_name}: {exc}",
        ) from exc
