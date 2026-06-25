from __future__ import annotations

from app.websockets.broadcaster import publish_global
from app.websockets.events import (
    WorkflowStartedEvent,
    WorkflowProgressEvent,
    WorkflowCompletedEvent,
)


class EventService:
    def __init__(self, project_id: str):
        self.project_id = project_id

    async def workflow_started(
        self,
        topic: str,
        total_agents: int,
        initiated_by: str,
    ):
        event = WorkflowStartedEvent(
            project_id=self.project_id,
            topic=topic,
            total_agents=total_agents,
            initiated_by=initiated_by,
        )

        await publish_global(event.to_ws_payload())

    async def workflow_progress(
        self,
        current_agent: str,
        completed_agents: int,
        total_agents: int,
        message: str,
    ):
        percent = (
            completed_agents / max(total_agents, 1)
        ) * 100

        event = WorkflowProgressEvent(
            project_id=self.project_id,
            current_agent=current_agent,
            completed_agents=completed_agents,
            total_agents=total_agents,
            percent_complete=percent,
            message=message,
        )

        await publish_global(event.to_ws_payload())

    async def workflow_completed(
        self,
        duration_seconds: float,
        papers_retrieved: int,
        sections_generated: int,
        tokens_used: int,
    ):
        event = WorkflowCompletedEvent(
            project_id=self.project_id,
            duration_seconds=duration_seconds,
            papers_retrieved=papers_retrieved,
            sections_generated=sections_generated,
            tokens_used=tokens_used,
        )

        await publish_global(event.to_ws_payload())