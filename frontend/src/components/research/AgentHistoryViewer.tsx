'use client';

import React, { useState } from 'react';
import { AgentHistoryEntry } from '@/types';
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
  Activity,
  XCircle,
  Loader2,
  Clock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from 'lucide-react';

interface AgentHistoryViewerProps {
  history: AgentHistoryEntry[];
  errors?: any[];
}

/**
 * Ordered agent icon/color mapping — reuses the PIPELINE concept from
 * WorkflowTimeline.tsx but for historical (persisted) data.
 */
const AGENT_CONFIG: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; badgeColor: string }> = {
  research_retrieval:      { label: 'Paper Retrieval',       icon: Search,        badgeColor: 'bg-blue-50 text-blue-700 border-blue-200' },
  literature_review:       { label: 'Literature Review',     icon: BookOpen,      badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  citation_verification:   { label: 'Citation Verification', icon: CheckCircle2,  badgeColor: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  gap_analysis:            { label: 'Gap Analysis',          icon: Lightbulb,     badgeColor: 'bg-purple-50 text-purple-700 border-purple-200' },
  methodology_suggestion:  { label: 'Methodology',           icon: FlaskConical,  badgeColor: 'bg-teal-50 text-teal-700 border-teal-200' },
  draft_writing:           { label: 'Draft Writing',         icon: PenTool,       badgeColor: 'bg-violet-50 text-violet-700 border-violet-200' },
  hallucination_detection: { label: 'Hallucination Check',   icon: ShieldCheck,   badgeColor: 'bg-amber-50 text-amber-700 border-amber-200' },
  formatting:              { label: 'Formatting',            icon: FileType2,     badgeColor: 'bg-sky-50 text-sky-700 border-sky-200' },
  journal_recommendation:  { label: 'Journal Matching',      icon: BookMarked,    badgeColor: 'bg-orange-50 text-orange-700 border-orange-200' },
  reviewer_simulation:     { label: 'Peer Review Sim',       icon: Users,         badgeColor: 'bg-rose-50 text-rose-700 border-rose-200' },
  submission_preparation:  { label: 'Submission Prep',       icon: Package,       badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
};

const DEFAULT_CONFIG = {
  label: 'Agent',
  icon: Activity,
  badgeColor: 'bg-gray-50 text-gray-700 border-gray-200',
};

/**
 * Displays the agent_history array from workflow_state as a structured
 * vertical timeline. Shows agent name, status, timestamp, and elapsed time.
 */
export default function AgentHistoryViewer({ history, errors }: AgentHistoryViewerProps) {
  const [showErrors, setShowErrors] = useState(false);
  const hasErrors = errors && errors.length > 0;

  if (!history || history.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
          <Clock className="w-3 h-3" />
          Agent History
          <span className="font-mono tabular-nums text-gray-400">({history.length})</span>
        </h3>

        {hasErrors && (
          <button
            onClick={() => setShowErrors(!showErrors)}
            className="flex items-center gap-1 text-[11px] text-red-600 font-medium hover:text-red-700 transition-colors"
          >
            <AlertTriangle className="w-3 h-3" />
            {errors.length} error{errors.length !== 1 ? 's' : ''}
            {showErrors ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
          </button>
        )}
      </div>

      {/* Error panel */}
      {showErrors && hasErrors && (
        <div className="px-5 py-3 bg-red-50 border-b border-red-100 space-y-2">
          {errors.map((err, idx) => (
            <div key={idx} className="text-xs text-red-700 font-mono whitespace-pre-wrap select-text">
              {typeof err === 'string' ? err : JSON.stringify(err, null, 2)}
            </div>
          ))}
        </div>
      )}

      {/* Timeline */}
      <div className="px-5 py-4">
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[11px] top-2 bottom-2 w-px bg-gray-200" />

          <div className="space-y-0.5">
            {history.map((entry, idx) => {
              const config = AGENT_CONFIG[entry.agent] ?? DEFAULT_CONFIG;
              const Icon = config.icon;
              const isCompleted = entry.status === 'completed';
              const isFailed = entry.status === 'failed' || entry.status === 'error';
              const isRunning = entry.status === 'running' || entry.status === 'in_progress';

              const formattedTime = entry.timestamp
                ? new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                : '';

              const elapsed = entry.elapsed_seconds != null
                ? entry.elapsed_seconds < 60
                  ? `${entry.elapsed_seconds.toFixed(1)}s`
                  : `${Math.floor(entry.elapsed_seconds / 60)}m ${Math.round(entry.elapsed_seconds % 60)}s`
                : null;

              return (
                <div
                  key={`${entry.agent}-${idx}`}
                  className={`relative flex items-center gap-3 py-2 px-1 rounded-md transition-colors ${
                    isRunning ? 'bg-indigo-50' : ''
                  }`}
                >
                  {/* Status dot */}
                  <div className="relative z-10 shrink-0">
                    {isCompleted ? (
                      <div className="w-[22px] h-[22px] rounded-full bg-emerald-100 flex items-center justify-center">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      </div>
                    ) : isFailed ? (
                      <div className="w-[22px] h-[22px] rounded-full bg-red-100 flex items-center justify-center">
                        <XCircle className="w-3.5 h-3.5 text-red-600" />
                      </div>
                    ) : isRunning ? (
                      <div className="w-[22px] h-[22px] rounded-full bg-indigo-600 flex items-center justify-center timeline-dot-active">
                        <Loader2 className="w-3 h-3 text-white animate-spin" />
                      </div>
                    ) : (
                      <div className="w-[22px] h-[22px] rounded-full bg-gray-100 flex items-center justify-center">
                        <Activity className="w-3 h-3 text-gray-400" />
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Icon className={`w-3.5 h-3.5 shrink-0 ${
                        isCompleted ? 'text-emerald-600' :
                        isFailed ? 'text-red-500' :
                        isRunning ? 'text-indigo-600' :
                        'text-gray-400'
                      }`} />
                      <span className={`text-sm truncate ${
                        isCompleted ? 'text-gray-700' :
                        isFailed ? 'text-red-600' :
                        isRunning ? 'text-indigo-700 font-medium' :
                        'text-gray-500'
                      }`}>
                        {config.label}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border capitalize shrink-0 ${
                        isCompleted ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        isFailed ? 'bg-red-50 text-red-700 border-red-200' :
                        isRunning ? 'bg-indigo-50 text-indigo-700 border-indigo-200' :
                        'bg-gray-50 text-gray-500 border-gray-200'
                      }`}>
                        {entry.status}
                      </span>
                    </div>

                    {/* Timing info */}
                    <div className="flex items-center gap-2 shrink-0">
                      {elapsed && (
                        <span className="text-[11px] text-gray-400 font-mono tabular-nums">
                          {elapsed}
                        </span>
                      )}
                      {formattedTime && (
                        <span className="text-[11px] text-gray-300 font-mono tabular-nums hidden sm:inline">
                          {formattedTime}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
