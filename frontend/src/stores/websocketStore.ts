import { create } from "zustand";
import {
    AnyWSEvent,
    EventType,
    WorkflowProgressEvent,
    AgentStartedEvent,
    AgentCompletedEvent,
    AgentFailedEvent,
    DraftUpdatedEvent,
    ConnectionAckEvent,
} from "@/types/websocket";

interface WebSocketState {
    connected: boolean;
    connectionId: string | null;

    workflowStatus: string | null;
    progress: number;

    currentAgent: string | null;

    draftSections: Record<string, string>;

    events: AnyWSEvent[];

    setConnected: (connected: boolean) => void;

    handleEvent: (event: AnyWSEvent) => void;

    reset: () => void;
}

export const useWebSocketStore = create<WebSocketState>((set) => ({
    connected: false,

    connectionId: null,

    workflowStatus: null,

    progress: 0,

    currentAgent: null,

    draftSections: {},

    events: [],

    setConnected: (connected) =>
        set({
            connected,
        }),

    handleEvent: (event) => {
        set((state) => {
            const nextEvents = [...state.events, event].slice(-500);

            const update: Partial<WebSocketState> = {
                events: nextEvents,
            };

            switch (event.event_type) {
                case EventType.CONNECTION_ACK: {
                    const e = event as ConnectionAckEvent;

                    update.connected = true;
                    update.connectionId = e.connection_id;
                    break;
                }

                case EventType.WORKFLOW_STARTED: {
                    update.workflowStatus = "running";
                    update.progress = 0;
                    break;
                }

                case EventType.WORKFLOW_PROGRESS: {
                    const e = event as WorkflowProgressEvent;

                    update.progress = e.percent_complete;
                    update.currentAgent = e.current_agent;
                    break;
                }

                case EventType.WORKFLOW_COMPLETED: {
                    update.workflowStatus = "completed";
                    update.progress = 100;
                    break;
                }

                case EventType.WORKFLOW_FAILED: {
                    update.workflowStatus = "failed";
                    break;
                }

                case EventType.AGENT_STARTED: {
                    const e = event as AgentStartedEvent;

                    update.currentAgent = e.agent_name;
                    break;
                }

                case EventType.AGENT_COMPLETED: {
                    const e = event as AgentCompletedEvent;

                    update.currentAgent = e.agent_name;
                    break;
                }

                case EventType.AGENT_FAILED: {
                    const e = event as AgentFailedEvent;

                    update.currentAgent = e.agent_name;
                    break;
                }

                case EventType.DRAFT_UPDATED: {
                    const e = event as DraftUpdatedEvent;

                    update.draftSections = {
                        ...state.draftSections,
                        [e.section_id]:
                            (state.draftSections[e.section_id] || "") +
                            e.content_chunk,
                    };

                    break;
                }
            }

            return update;
        });
    },

    reset: () =>
        set({
            connected: false,
            connectionId: null,
            workflowStatus: null,
            progress: 0,
            currentAgent: null,
            draftSections: {},
            events: [],
        }),
}));