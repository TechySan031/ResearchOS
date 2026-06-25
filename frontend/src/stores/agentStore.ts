import { create } from 'zustand';
import { api } from '../lib/api';
import { Paper, Citation, DocumentSection, AgentLog, ResearchStatus } from '../types';

interface AgentState {
  papers: Paper[];
  citations: Citation[];
  documentSections: DocumentSection[];
  agentLogs: AgentLog[];
  researchStatus: ResearchStatus | null;
  streamingContent: Record<string, string>;
  activeAgent: string | null;
  metrics: {
    ttftMs: number | null;
    workflowDurationMs: number | null;
  };
  isLoading: boolean;
  error: string | null;


  fetchPapers: (projectId: string) => Promise<void>;
  fetchCitations: (projectId: string) => Promise<void>;
  fetchDocumentSections: (projectId: string) => Promise<void>;
  fetchAgentLogs: (projectId: string) => Promise<void>;
  fetchResearchStatus: (projectId: string) => Promise<void>;
  startResearch: (projectId: string, payload: { search_queries?: string[]; max_papers?: number; format_style?: string }) => Promise<ResearchStatus>;
  pauseResearch: (projectId: string) => Promise<void>;
  resumeResearch: (projectId: string) => Promise<void>;
  cancelResearch: (projectId: string) => Promise<void>;
  updateSectionContent: (projectId: string, sectionId: string, content: string) => Promise<void>;

  // Real-time websocket mutations
  addAgentLog: (log: AgentLog) => void;
  setResearchStatus: (status: ResearchStatus | null) => void;
  appendStreamingContent: (section: string, token: string) => void;

  recordMetric: (metric: {
    metric_type: string;
    value: number;
  }) => void

  clearStreamingContent: () => void;
  reset: () => void;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  papers: [],
  citations: [],
  documentSections: [],
  agentLogs: [],
  researchStatus: null,
  streamingContent: {},
  activeAgent: null,

  metrics: {
    ttftMs: null,
    workflowDurationMs: null,
  },
  isLoading: false,
  error: null,

  fetchPapers: async (projectId: string) => {
    try {
      const data = await api.get<Paper[]>(`/api/v1/projects/${projectId}/papers`);
      set({ papers: data });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch papers' });
    }
  },

  fetchCitations: async (projectId: string) => {
    try {
      const data = await api.get<Citation[]>(`/api/v1/projects/${projectId}/citations`);
      set({ citations: data });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch citations' });
    }
  },

  fetchDocumentSections: async (projectId: string) => {
    try {
      const data = await api.get<DocumentSection[]>(`/api/v1/projects/${projectId}/document`);
      set({ documentSections: data });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch document sections' });
    }
  },

  fetchAgentLogs: async (projectId: string) => {
    try {
      const data = await api.get<AgentLog[]>(`/api/v1/projects/${projectId}/agents/logs`);
      set({ agentLogs: data });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch agent logs' });
    }
  },

  fetchResearchStatus: async (projectId: string) => {
    try {
      const data = await api.get<ResearchStatus>(`/api/v1/projects/${projectId}/research/status`);
      set({ researchStatus: data, activeAgent: data.current_agent || null });
    } catch (err: any) {
      // If 404, workflow hasn't started yet
      set({ researchStatus: null, activeAgent: null });
    }
  },

  startResearch: async (projectId: string, payload) => {
    set({ isLoading: true, error: null });
    try {
      const status = await api.post<ResearchStatus>(`/api/v1/projects/${projectId}/research/start`, {
        project_id: projectId,
        ...payload,
      });
      set({ researchStatus: status, activeAgent: status.current_agent || null, isLoading: false });
      return status;
    } catch (err: any) {
      set({ error: err.message || 'Failed to start research workflow', isLoading: false });
      throw err;
    }
  },

  pauseResearch: async (projectId: string) => {
    try {
      await api.post(`/api/v1/projects/${projectId}/research/pause`);
      set((state) => ({
        researchStatus: state.researchStatus ? { ...state.researchStatus, status: 'paused' } : null,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to pause research' });
    }
  },

  resumeResearch: async (projectId: string) => {
    try {
      await api.post(`/api/v1/projects/${projectId}/research/resume`);
      set((state) => ({
        researchStatus: state.researchStatus ? { ...state.researchStatus, status: 'running' } : null,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to resume research' });
    }
  },

  cancelResearch: async (projectId: string) => {
    try {
      await api.post(`/api/v1/projects/${projectId}/research/cancel`);
      set((state) => ({
        researchStatus: state.researchStatus ? { ...state.researchStatus, status: 'cancelled' } : null,
        activeAgent: null,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to cancel research' });
    }
  },

  updateSectionContent: async (projectId: string, sectionId: string, content: string) => {
    try {
      const updatedSection = await api.patch<DocumentSection>(
        `/api/v1/projects/${projectId}/document/${sectionId}`,
        { content }
      );
      set((state) => ({
        documentSections: state.documentSections.map((s) => (s.id === sectionId ? updatedSection : s)),
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to update section content' });
    }
  },

  addAgentLog: (log) => {
    set((state) => {
      const logs = [...state.agentLogs, log];
      return {
        agentLogs: logs.slice(-500),
        activeAgent: log.agent_name,
      };
    });
  },

  setResearchStatus: (status) => {
    const isTerminal = !status || ['completed', 'failed', 'cancelled'].includes(status.status);
    set({
      researchStatus: status,
      activeAgent: status?.current_agent || null,
      ...(isTerminal ? { streamingContent: {} } : {}),
    });
  },

  appendStreamingContent: (section, token) => {
    set((state) => {
      const current = state.streamingContent[section] || '';
      return {
        streamingContent: {
          ...state.streamingContent,
          [section]: current + token,
        },
      };
    });
  },

  recordMetric: (metric) => {
    set((state) => {
      const metrics = { ...state.metrics };

      if (metric.metric_type === 'ttft_ms') {
        metrics.ttftMs = metric.value;
      }

      if (metric.metric_type === 'workflow_duration_ms') {
        metrics.workflowDurationMs = metric.value;
      }

      return { metrics };
    });
  },

  clearStreamingContent: () => {
    set({ streamingContent: {} });
  },

  reset: () => {
    set({
      papers: [],
      citations: [],
      documentSections: [],
      agentLogs: [],
      researchStatus: null,
      streamingContent: {},
      activeAgent: null,
      metrics: {
        ttftMs: null,
        workflowDurationMs: null,
      },
      error: null,
    });
  },
}));
