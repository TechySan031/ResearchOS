export interface Project {
  id: string;
  title: string;
  description?: string;
  topic?: string;
  status: 'created' | 'researching' | 'drafting' | 'reviewing' | 'completed' | 'failed';
  workflow_state?: Record<string, any>;
  settings_json?: Record<string, any>;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface Paper {
  id: string;
  project_id: string;
  title: string;
  abstract?: string;
  authors?: Record<string, any> | string[];
  doi?: string;
  url?: string;
  source: string;
  year?: number;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface Citation {
  id: string;
  project_id: string;
  paper_id?: string;
  citation_key: string;
  formatted_text?: string;
  status: 'verified' | 'unverified' | 'failed';
  verification_details?: Record<string, any>;
  created_at: string;
}

export interface DocumentSection {
  id: string;
  project_id: string;
  title: string;
  content?: string;
  section_order: number;
  section_type: string;
  word_count?: number;
  created_at: string;
  updated_at: string;
}

export interface AgentLog {
  id: string;
  project_id: string;
  agent_name: string;
  event_type: string;
  message?: string;
  data?: Record<string, any>;
  tokens_used?: number;
  duration_ms?: number;
  created_at: string;
}

export interface ResearchStatus {
  project_id: string;
  status: string;
  current_agent?: string;
  progress_pct: number;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface WebSocketEventMessage {
  type: string;
  project_id?: string;
  data: Record<string, any>;
  timestamp?: string;
}

// ─── Workflow State Types (matches backend schema exactly) ────────────

export interface RetrievedPaper {
  title: string;
  authors: string[];
  abstract: string;
  year: number;
  doi: string;
  source: string;
  citation_count: number;
  url: string;
}

export interface AgentHistoryEntry {
  agent: string;
  status: string;
  timestamp: string;
  elapsed_seconds?: number;
}

export interface WorkflowState {
  topic: string;
  project_id: string;
  user_preferences: Record<string, any>;

  retrieved_papers: RetrievedPaper[];
  paper_embeddings_stored: boolean;

  literature_review: string;
  key_themes: string[];

  citations: any[];
  citation_verification_results: any[];

  research_gaps: any[];
  gap_analysis_completed: boolean;

  suggested_methodologies: any[];
  selected_methodology: any;

  paper_outline: Record<string, any>;
  paper_sections: Record<string, string>;

  hallucination_report: any;

  formatted_paper: string;
  format_style: string;

  journal_recommendations: any[];
  reviewer_feedback: any[];

  submission_package: any;

  current_agent: string;

  agent_history: AgentHistoryEntry[];

  errors: any[];
  status: string;

  revision_count: number;
  max_revisions: number;
}

/**
 * Safely extract and cast workflow_state from a Project.
 * Returns null if workflow_state is missing or empty.
 */
export function getWorkflowState(project: Project | null): WorkflowState | null {
  if (!project?.workflow_state) return null;
  const ws = project.workflow_state;
  // Check if it has at least one meaningful field populated
  if (Object.keys(ws).length === 0) return null;
  return ws as WorkflowState;
}

// ─── Copilot Types ────────────────────────────────────────────────────

export interface CopilotMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  timestamp: string;
}

export interface CopilotChatRequest {
  message: string;
}

export interface CopilotChatResponse {
  answer: string;
  sources: string[];
}

// ─── Auth Types ───────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'researcher' | 'viewer';
  created_at: string;
  updated_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ─── Audit Log Types ─────────────────────────────────────────────────

export interface AuditLogEntry {
  id: string;
  user_id?: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  detail?: string;
  ip_address?: string;
  created_at: string;
}
