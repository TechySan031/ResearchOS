import { useEffect, useRef, useState, useCallback } from 'react';
import { useAgentStore } from '../stores/agentStore';
import { useProjectStore } from '../stores/projectStore';
import { api } from '../lib/api';
import { AgentLog, ResearchStatus } from '../types';

const isDev = process.env.NODE_ENV === 'development';

export function useWebSocket(projectId: string | undefined) {
  const socketRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addAgentLog = useAgentStore((state) => state.addAgentLog);
  const setResearchStatus = useAgentStore((state) => state.setResearchStatus);
  const fetchPapers = useAgentStore((state) => state.fetchPapers);
  const fetchCitations = useAgentStore((state) => state.fetchCitations);
  const fetchDocumentSections = useAgentStore((state) => state.fetchDocumentSections);
  const fetchAgentLogs = useAgentStore((state) => state.fetchAgentLogs);
  const fetchResearchStatus = useAgentStore((state) => state.fetchResearchStatus);

  // Project store — refresh workflow_state after agent/workflow events
  const fetchProject = useProjectStore((state) => state.fetchProject);

  const connect = useCallback(() => {
    if (!projectId) return;

    // Close existing socket if any and discard its event listeners
    if (socketRef.current) {
      socketRef.current.onopen = null;
      socketRef.current.onmessage = null;
      socketRef.current.onerror = null;
      socketRef.current.onclose = null;
      socketRef.current.close();
    }

    const baseUrl = api.baseUrl;
    const wsUrl = baseUrl.replace(/^http/, 'ws') + `/api/v1/ws/${projectId}`;

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        console.log("WS EVENT:", msg);

        switch (msg.type) {
          case 'connected':
            break;

          case 'agent_started':
          case 'agent_progress':
          case 'agent_completed':
          case 'agent_error':
          case 'agent_event': {
            // Reconstruct AgentLog shape
            const logData: AgentLog = {
              id: Math.random().toString(36).substring(7),
              project_id: projectId,
              agent_name: msg.agent || 'system',
              event_type: msg.type,
              message: msg.data?.message || msg.data?.text || `Agent ${msg.agent} event`,
              data: msg.data,
              created_at: msg.timestamp || new Date().toISOString(),
            };
            addAgentLog(logData);

            // Refetch data when agent completes key tasks to sync state
            if (msg.type === 'agent_completed') {
              fetchPapers(projectId);
              fetchCitations(projectId);
              fetchDocumentSections(projectId);
              fetchAgentLogs(projectId);
              fetchResearchStatus(projectId);
              // Refresh project to update workflow_state for Phase 2 components
              fetchProject(projectId);
            }
            break;
          }

          // stream_token events are handled exclusively by SSE (useSSE hook).
          // Do not handle them here to avoid duplicate token delivery.

          case 'workflow_status': {
            const statusData: ResearchStatus = {
              project_id: projectId,
              status: msg.data?.status || 'running',
              current_agent: msg.data?.current_agent,
              progress_pct: msg.data?.progress || 0,
            };
            setResearchStatus(statusData);
            break;
          }

          case 'workflow_completed': {
            const completedStatus: ResearchStatus = {
              project_id: projectId,
              status: 'completed',
              progress_pct: 100,
            };
            setResearchStatus(completedStatus);
            // streamingContent is cleared automatically by setResearchStatus (Fix 6)
            fetchPapers(projectId);
            fetchCitations(projectId);
            fetchDocumentSections(projectId);
            fetchAgentLogs(projectId);
            // Refresh project to update workflow_state for Phase 2 components
            fetchProject(projectId);
            break;
          }

          case 'pong':
            break;

          default:
            if (isDev) {
              // Only log unhandled events in development
              // eslint-disable-next-line no-console
              console.log('Unhandled WS event:', msg.type);
            }
        }
      } catch (err) {
        if (isDev) {
          // eslint-disable-next-line no-console
          console.error('WS message parse error:', err);
        }
      }
    };

    socket.onerror = () => {
      setError('WebSocket connection error');
    };

    socket.onclose = (event) => {
      setIsConnected(false);

      if (event.code !== 1000 && projectId) {
        setTimeout(() => connect(), 3000);
      }
    };
  }, [
    projectId,
    addAgentLog,
    setResearchStatus,
    fetchPapers,
    fetchCitations,
    fetchDocumentSections,
    fetchAgentLogs,
    fetchResearchStatus,
    fetchProject,
  ]);

  useEffect(() => {
    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.onopen = null;
        socketRef.current.onmessage = null;
        socketRef.current.onerror = null;
        socketRef.current.onclose = null;
        socketRef.current.close(1000);
        socketRef.current = null;
      }
      setIsConnected(false);
    };
  }, [connect]);

  const sendInput = useCallback((agent: string, data: Record<string, any>) => {
    if (socketRef.current && isConnected) {
      socketRef.current.send(
        JSON.stringify({
          type: 'user_input',
          agent,
          data,
        })
      );
    }
  }, [isConnected]);

  return { isConnected, error, sendInput };
}
