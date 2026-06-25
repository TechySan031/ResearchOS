import { useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import { useAgentStore } from '@/stores/agentStore';

/**
 * React hook that connects to the SSE streaming endpoint for a project.
 *
 * Uses the browser-native `EventSource` API which:
 * - Reconnects automatically on network failure
 * - Handles `text/event-stream` parsing natively
 * - Is unidirectional (server → client only)
 *
 * Forwards `stream_token` events to the Zustand store for rendering
 * by the `StreamingContent` component.
 *
 * @param projectId - The UUID of the project to stream events for.
 *                    Pass `null` to disconnect.
 */
export function useSSE(projectId: string | null) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const appendStreamingContent = useAgentStore(
    (s) => s.appendStreamingContent
  );
  const recordMetric = useAgentStore(
    (s) => s.recordMetric
  );

  const connect = useCallback(() => {
    if (!projectId) return;

    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = `${api.baseUrl}/api/v1/projects/${projectId}/stream`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    // Handle streaming tokens
    es.addEventListener('stream_token', (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data);
        const token = payload.data?.token;
        const section = payload.data?.section || 'draft';
        if (token) {
          appendStreamingContent(section, token);
        }
      } catch {
        // Silently ignore parse errors
      }
    });

    es.addEventListener(
      'metric_recorded',
      (event: MessageEvent) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload.data) {
            recordMetric(payload.data);
          }
        } catch {
          // ignore parse errors
        }
      });

    // Handle connection established — do NOT clear content on reconnect
    // to preserve accumulated streaming text after network blips.
    // Cleanup on workflow end is handled by setResearchStatus (Fix 6).
    es.addEventListener('connected', () => {
      // no-op
    });

    // Handle agent lifecycle events (for logging / debugging)
    es.addEventListener('agent_started', () => {
      // Handled by WebSocket — SSE is content-only
    });

    es.addEventListener('agent_completed', () => {
      // Handled by WebSocket
    });

    // Handle workflow completion — close SSE stream
    es.addEventListener('workflow_completed', () => {
      es.close();
    });

    es.addEventListener('workflow_failed', () => {
      es.close();
    });

    // Handle errors (EventSource auto-reconnects)
    es.onerror = () => {
      // EventSource will automatically attempt reconnection
      // No explicit handling needed
    };
  }, [
    projectId,
    appendStreamingContent,
    recordMetric,
  ]);

  useEffect(() => {
    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [connect]);
}
