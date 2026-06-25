from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_PROGRESS = "workflow_progress"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    DRAFT_UPDATED = "draft_updated"
    ARTIFACT_CREATED = "artifact_created"
    COPILOT_MESSAGE = "copilot_message"
    PING = "ping"
    PONG = "pong"
    CONNECTION_ACK = "connection_ack"
    ERROR = "error"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    project_id: str
    timestamp: str = Field(default_factory=_now_iso)

    def to_ws_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class WorkflowStartedEvent(BaseEvent):
    event_type: Literal[EventType.WORKFLOW_STARTED] = EventType.WORKFLOW_STARTED
    topic: str
    total_agents: int
    initiated_by: str


class WorkflowProgressEvent(BaseEvent):
    event_type: Literal[EventType.WORKFLOW_PROGRESS] = EventType.WORKFLOW_PROGRESS
    current_agent: str
    completed_agents: int
    total_agents: int
    percent_complete: float
    message: str


class WorkflowCompletedEvent(BaseEvent):
    event_type: Literal[EventType.WORKFLOW_COMPLETED] = EventType.WORKFLOW_COMPLETED
    duration_seconds: float
    papers_retrieved: int
    sections_generated: int
    tokens_used: int


class WorkflowFailedEvent(BaseEvent):
    event_type: Literal[EventType.WORKFLOW_FAILED] = EventType.WORKFLOW_FAILED
    failed_agent: str
    error_message: str
    retry_possible: bool = True


class AgentStartedEvent(BaseEvent):
    event_type: Literal[EventType.AGENT_STARTED] = EventType.AGENT_STARTED
    agent_name: str
    agent_description: str
    agent_index: int
    total_agents: int


class AgentCompletedEvent(BaseEvent):
    event_type: Literal[EventType.AGENT_COMPLETED] = EventType.AGENT_COMPLETED
    agent_name: str
    duration_seconds: float
    tokens_used: int
    output_summary: str
    artifacts_produced: list[str] = Field(default_factory=list)


class AgentFailedEvent(BaseEvent):
    event_type: Literal[EventType.AGENT_FAILED] = EventType.AGENT_FAILED
    agent_name: str
    error_message: str
    error_type: str
    duration_seconds: float
    retrying: bool = False


class DraftUpdatedEvent(BaseEvent):
    event_type: Literal[EventType.DRAFT_UPDATED] = EventType.DRAFT_UPDATED
    section_id: str
    section_title: str
    content_chunk: str
    is_final: bool
    word_count: int


class ArtifactCreatedEvent(BaseEvent):
    event_type: Literal[EventType.ARTIFACT_CREATED] = EventType.ARTIFACT_CREATED
    artifact_type: str
    artifact_id: str
    artifact_title: str
    agent_source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CopilotMessageEvent(BaseEvent):
    event_type: Literal[EventType.COPILOT_MESSAGE] = EventType.COPILOT_MESSAGE
    message_id: str
    role: Literal["assistant"]
    content: str
    is_streaming: bool
    is_final: bool
    context_sources: list[str] = Field(default_factory=list)


class PingEvent(BaseEvent):
    event_type: Literal[EventType.PING] = EventType.PING


class PongEvent(BaseEvent):
    event_type: Literal[EventType.PONG] = EventType.PONG


class ConnectionAckEvent(BaseEvent):
    event_type: Literal[EventType.CONNECTION_ACK] = EventType.CONNECTION_ACK
    connection_id: str
    user_id: str
    subscribed_to: str


class ErrorEvent(BaseEvent):
    event_type: Literal[EventType.ERROR] = EventType.ERROR
    code: str
    message: str
    recoverable: bool = True


AnyEvent = (
    WorkflowStartedEvent
    | WorkflowProgressEvent
    | WorkflowCompletedEvent
    | WorkflowFailedEvent
    | AgentStartedEvent
    | AgentCompletedEvent
    | AgentFailedEvent
    | DraftUpdatedEvent
    | ArtifactCreatedEvent
    | CopilotMessageEvent
    | PingEvent
    | PongEvent
    | ConnectionAckEvent
    | ErrorEvent
)