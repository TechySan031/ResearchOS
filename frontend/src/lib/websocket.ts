import type { AnyWSEvent, EventType, WSEventMap } from "@/types/websocket";

const BASE_WS_URL =
    process.env.NEXT_PUBLIC_WS_URL ??
    process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, "ws") ??
    "ws://localhost:8000";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const RECONNECT_MAX_ATTEMPTS = 10;
const PING_INTERVAL_MS = 25000;

type EventHandler<T extends EventType> = (event: WSEventMap[T]) => void;
type AnyHandler = (event: AnyWSEvent) => void;

type ListenerMap = {
    [K in EventType]?: Set<EventHandler<K>>;
};

export type ConnectionState =
    | "connecting"
    | "connected"
    | "reconnecting"
    | "disconnected";

export interface WSClientOptions {
    projectId: string;
    token: string;
    onStateChange?: (state: ConnectionState) => void;
    onError?: (error: Event) => void;
}

export class ResearchWSClient {
    private ws: WebSocket | null = null;
    private listeners: ListenerMap = {};
    private catchAllListeners = new Set<AnyHandler>();

    private reconnectAttempts = 0;
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private pingTimer: ReturnType<typeof setInterval> | null = null;

    private state: ConnectionState = "disconnected";
    private destroyed = false;

    constructor(private opts: WSClientOptions) { }

    connect(): void {
        if (this.destroyed) return;

        if (
            this.ws?.readyState === WebSocket.OPEN ||
            this.ws?.readyState === WebSocket.CONNECTING
        ) {
            return;
        }

        this.setState(
            this.reconnectAttempts === 0 ? "connecting" : "reconnecting"
        );

        const url =
            `${BASE_WS_URL}/api/v1/ws/projects/` +
            `${this.opts.projectId}?token=${encodeURIComponent(this.opts.token)}`;

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            this.setState("connected");
            this.startPing();
        };

        this.ws.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data) as AnyWSEvent;

                if (parsed.event_type === "ping") {
                    this.send({
                        event_type: "pong",
                        project_id: this.opts.projectId,
                    });
                    return;
                }

                const handlers =
                    this.listeners[parsed.event_type as EventType];

                handlers?.forEach((h) => {
                    (h as AnyHandler)(parsed);
                });

                this.catchAllListeners.forEach((h) => h(parsed));
            } catch {
                // ignore malformed messages
            }
        };

        this.ws.onclose = (event) => {
            this.clearTimers();

            if (this.destroyed || event.code === 1000) {
                this.setState("disconnected");
                return;
            }

            this.scheduleReconnect();
        };

        this.ws.onerror = (event) => {
            this.opts.onError?.(event);
        };
    }

    disconnect(): void {
        this.destroyed = true;

        this.clearTimers();

        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        this.setState("disconnected");
    }

    send(payload: Record<string, unknown>): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(payload));
        }
    }

    on<T extends EventType>(
        type: T,
        handler: EventHandler<T>
    ): () => void {
        if (!this.listeners[type]) {
            (this.listeners as Record<string, Set<unknown>>)[type] = new Set();
        }

        (this.listeners[type] as Set<EventHandler<T>>).add(handler);

        return () => this.off(type, handler);
    }

    off<T extends EventType>(
        type: T,
        handler: EventHandler<T>
    ): void {
        (this.listeners[type] as Set<EventHandler<T>> | undefined)?.delete(
            handler
        );
    }

    onAny(handler: AnyHandler): () => void {
        this.catchAllListeners.add(handler);
        return () => this.catchAllListeners.delete(handler);
    }

    getState(): ConnectionState {
        return this.state;
    }

    private startPing(): void {
        this.clearPing();

        this.pingTimer = setInterval(() => {
            this.send({
                event_type: "ping",
                project_id: this.opts.projectId,
            });
        }, PING_INTERVAL_MS);
    }

    private clearPing(): void {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }

    private clearTimers(): void {
        this.clearPing();

        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }

    private scheduleReconnect(): void {
        if (this.reconnectAttempts >= RECONNECT_MAX_ATTEMPTS) {
            this.setState("disconnected");
            return;
        }

        const delay = Math.min(
            RECONNECT_BASE_MS * Math.pow(2, this.reconnectAttempts),
            RECONNECT_MAX_MS
        );

        this.reconnectAttempts++;

        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, delay);
    }

    private setState(state: ConnectionState): void {
        this.state = state;
        this.opts.onStateChange?.(state);
    }
}