export enum EventType {
    WORKFLOW_STARTED = "workflow_started",
    WORKFLOW_PROGRESS = "workflow_progress",
    WORKFLOW_COMPLETED = "workflow_completed",
    WORKFLOW_FAILED = "workflow_failed",
    AGENT_STARTED = "agent_started",
    AGENT_COMPLETED = "agent_completed",
    AGENT_FAILED = "agent_failed",
    DRAFT_UPDATED = "draft_updated",
    ARTIFACT_CREATED = "artifact_created",
    COPILOT_MESSAGE = "copilot_message",
    PING = "ping",
    PONG = "pong",
    CONNECTION_ACK = "connection_ack",
    ERROR = "error",
}

export interface BaseEvent {
    event_id: string;
    event_type: EventType;
    project_id: string;
    timestamp: string;
}

export interface WorkflowStartedEvent extends BaseEvent {
    event_type: EventType.WORKFLOW_STARTED;
    topic: string;
    total_agents: number;
    initiated_by: string;
}

export interface WorkflowProgressEvent extends BaseEvent {
    event_type: EventType.WORKFLOW_PROGRESS;
    current_agent: string;
    completed_agents: number;
    total_agents: number;
    percent_complete: number;
    message: string;
}

export interface WorkflowCompletedEvent extends BaseEvent {
    event_type: EventType.WORKFLOW_COMPLETED;
    duration_seconds: number;
    papers_retrieved: number;
    sections_generated: number;
    tokens_used: number;
}

export interface WorkflowFailedEvent extends BaseEvent {
    event_type: EventType.WORKFLOW_FAILED;
    failed_agent: string;
    error_message: string;
    retry_possible: boolean;
}

export interface AgentStartedEvent extends BaseEvent {
    event_type: EventType.AGENT_STARTED;
    agent_name: string;
    agent_description: string;
    agent_index: number;
    total_agents: number;
}

export interface AgentCompletedEvent extends BaseEvent {
    event_type: EventType.AGENT_COMPLETED;
    agent_name: string;
    duration_seconds: number;
    tokens_used: number;
    output_summary: string;
    artifacts_produced: string[];
}

export interface AgentFailedEvent extends BaseEvent {
    event_type: EventType.AGENT_FAILED;
    agent_name: string;
    error_message: string;
    error_type: string;
    duration_seconds: number;
    retrying: boolean;
}

export interface DraftUpdatedEvent extends BaseEvent {
    event_type: EventType.DRAFT_UPDATED;
    section_id: string;
    section_title: string;
    content_chunk: string;
    is_final: boolean;
    word_count: number;
}

export interface ArtifactCreatedEvent extends BaseEvent {
    event_type: EventType.ARTIFACT_CREATED;
    artifact_type: string;
    artifact_id: string;
    artifact_title: string;
    agent_source: string;
    metadata: Record<string, unknown>;
}

export interface CopilotMessageEvent extends BaseEvent {
    event_type: EventType.COPILOT_MESSAGE;
    message_id: string;
    role: "assistant";
    content: string;
    is_streaming: boolean;
    is_final: boolean;
    context_sources: string[];
}

export interface PingEvent extends BaseEvent {
    event_type: EventType.PING;
}

export interface PongEvent extends BaseEvent {
    event_type: EventType.PONG;
}

export interface ConnectionAckEvent extends BaseEvent {
    event_type: EventType.CONNECTION_ACK;
    connection_id: string;
    user_id: string;
    subscribed_to: string;
}

export interface ErrorEvent extends BaseEvent {
    event_type: EventType.ERROR;
    code: string;
    message: string;
    recoverable: boolean;
}

export type AnyWSEvent =
    | WorkflowStartedEvent
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
    | ErrorEvent;

export interface WSEventMap {
    [EventType.WORKFLOW_STARTED]: WorkflowStartedEvent;
    [EventType.WORKFLOW_PROGRESS]: WorkflowProgressEvent;
    [EventType.WORKFLOW_COMPLETED]: WorkflowCompletedEvent;
    [EventType.WORKFLOW_FAILED]: WorkflowFailedEvent;
    [EventType.AGENT_STARTED]: AgentStartedEvent;
    [EventType.AGENT_COMPLETED]: AgentCompletedEvent;
    [EventType.AGENT_FAILED]: AgentFailedEvent;
    [EventType.DRAFT_UPDATED]: DraftUpdatedEvent;
    [EventType.ARTIFACT_CREATED]: ArtifactCreatedEvent;
    [EventType.COPILOT_MESSAGE]: CopilotMessageEvent;
    [EventType.PING]: PingEvent;
    [EventType.PONG]: PongEvent;
    [EventType.CONNECTION_ACK]: ConnectionAckEvent;
    [EventType.ERROR]: ErrorEvent;
};