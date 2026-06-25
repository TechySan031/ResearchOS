'use client';

import React from 'react';
import { AgentLog } from '@/types';
import {
  Search,
  BookOpen,
  CheckCircle2,
  Lightbulb,
  FlaskConical,
  PenTool,
  ShieldCheck,
  FileType2,
  BookMarked,
  Users,
  Package,
  Circle,
  XCircle,
  Loader2,
} from 'lucide-react';

interface WorkflowTimelineProps {
  logs: AgentLog[];
  activeAgent: string | null;
  workflowStatus: string | null;
}

/**
 * Ordered pipeline of all agents in the research workflow.
 * Each entry maps to a LangGraph node name.
 */
const PIPELINE = [
  { key: 'research_retrieval', label: 'Paper Retrieval', icon: Search },
  { key: 'literature_review', label: 'Literature Review', icon: BookOpen },
  { key: 'citation_verification', label: 'Citation Verification', icon: CheckCircle2 },
  { key: 'gap_analysis', label: 'Gap Analysis', icon: Lightbulb },
  { key: 'methodology_suggestion', label: 'Methodology', icon: FlaskConical },
  { key: 'draft_writing', label: 'Draft Writing', icon: PenTool },
  { key: 'hallucination_detection', label: 'Hallucination Check', icon: ShieldCheck },
  { key: 'formatting', label: 'Formatting', icon: FileType2 },
  { key: 'journal_recommendation', label: 'Journal Matching', icon: BookMarked },
  { key: 'reviewer_simulation', label: 'Peer Review Sim', icon: Users },
  { key: 'submission_preparation', label: 'Submission Prep', icon: Package },
] as const;

/**
 * Determine the status of each agent from the event log.
 */
function buildAgentStatus(logs: AgentLog[], activeAgent: string | null) {
  const status: Record<string, 'pending' | 'active' | 'completed' | 'failed'> = {};

  // Initialize all as pending
  for (const step of PIPELINE) {
    status[step.key] = 'pending';
  }

  // Walk through logs to find completed / failed agents
  for (const log of logs) {
    const name = log.agent_name;
    if (log.event_type === 'completed' || log.event_type === 'agent_completed') {
      status[name] = 'completed';
    } else if (log.event_type === 'failed' || log.event_type === 'agent_error') {
      status[name] = 'failed';
    } else if (log.event_type === 'started' || log.event_type === 'agent_started') {
      // Only mark started if not already completed/failed
      if (status[name] === 'pending') {
        status[name] = 'active';
      }
    }
  }

  // Override with current active agent
  if (activeAgent && status[activeAgent] !== 'completed' && status[activeAgent] !== 'failed') {
    status[activeAgent] = 'active';
  }

  return status;
}

/**
 * Get duration for a completed agent from logs.
 */
function getAgentDuration(logs: AgentLog[], agentKey: string): string | null {
  const completedLog = logs.find(
    (l) => l.agent_name === agentKey && (l.event_type === 'completed' || l.event_type === 'agent_completed')
  );
  if (completedLog?.duration_ms) {
    const seconds = (completedLog.duration_ms / 1000).toFixed(1);
    return `${seconds}s`;
  }
  if (completedLog?.data?.elapsed) {
    return `${Number(completedLog.data.elapsed).toFixed(1)}s`;
  }
  return null;
}

export default function WorkflowTimeline({ logs, activeAgent, workflowStatus }: WorkflowTimelineProps) {
  const statuses = buildAgentStatus(logs, activeAgent);
  const isIdle = !workflowStatus || workflowStatus === 'idle' || workflowStatus === 'completed';

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          Agent Pipeline
        </h3>
      </div>

      {/* Timeline */}
      <div className="px-5 py-4">
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[11px] top-2 bottom-2 w-px bg-gray-200" />

          <div className="space-y-0.5">
            {PIPELINE.map((step, index) => {
              const status = statuses[step.key];
              const duration = getAgentDuration(logs, step.key);
              const Icon = step.icon;

              return (
                <div
                  key={step.key}
                  className={`relative flex items-center gap-3 py-2 px-1 rounded-md transition-colors ${
                    status === 'active' ? 'bg-indigo-50' : ''
                  }`}
                >
                  {/* Status dot / icon */}
                  <div className="relative z-10 shrink-0">
                    {status === 'completed' ? (
                      <div className="w-[22px] h-[22px] rounded-full bg-emerald-100 flex items-center justify-center">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      </div>
                    ) : status === 'active' ? (
                      <div className="w-[22px] h-[22px] rounded-full bg-indigo-600 flex items-center justify-center timeline-dot-active">
                        <Loader2 className="w-3 h-3 text-white animate-spin" />
                      </div>
                    ) : status === 'failed' ? (
                      <div className="w-[22px] h-[22px] rounded-full bg-red-100 flex items-center justify-center">
                        <XCircle className="w-3.5 h-3.5 text-red-600" />
                      </div>
                    ) : (
                      <div className="w-[22px] h-[22px] rounded-full bg-gray-100 flex items-center justify-center">
                        <Circle className="w-2.5 h-2.5 text-gray-300" />
                      </div>
                    )}
                  </div>

                  {/* Label */}
                  <div className="flex-1 min-w-0 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className={`w-3.5 h-3.5 shrink-0 ${
                        status === 'completed' ? 'text-emerald-600' :
                        status === 'active' ? 'text-indigo-600' :
                        status === 'failed' ? 'text-red-500' :
                        'text-gray-300'
                      }`} />
                      <span className={`text-sm ${
                        status === 'completed' ? 'text-gray-700' :
                        status === 'active' ? 'text-indigo-700 font-medium' :
                        status === 'failed' ? 'text-red-600' :
                        'text-gray-400'
                      }`}>
                        {step.label}
                      </span>
                    </div>

                    {/* Duration badge for completed */}
                    {status === 'completed' && duration && (
                      <span className="text-[11px] text-gray-400 font-mono tabular-nums">
                        {duration}
                      </span>
                    )}

                    {/* Active indicator */}
                    {status === 'active' && (
                      <span className="text-[11px] text-indigo-500 font-medium">
                        Running...
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Idle state message */}
        {isIdle && logs.length === 0 && (
          <p className="text-xs text-gray-400 text-center mt-4 py-2">
            Start the workflow to see agent progress.
          </p>
        )}
      </div>
    </div>
  );
}
