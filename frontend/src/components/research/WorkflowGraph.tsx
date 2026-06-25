'use client';

import React, { useState, useEffect, memo } from 'react';
import {
  Search,
  BookOpen,
  CheckCircle2,
  HelpCircle,
  Cpu,
  Edit3,
  AlertTriangle,
  FileText,
  Book,
  Users,
  Mail,
  XCircle,
  Loader2,
  Clock,
} from 'lucide-react';

interface WorkflowGraphProps {
  currentAgent: string | null;
  status: string;
  progressPct?: number;
  startedAt?: string;
}

interface AgentNode {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const NODES: AgentNode[] = [
  { id: 'research_retrieval', label: 'Retrieval', icon: Search, description: 'Finds papers on arXiv, CrossRef, etc.' },
  { id: 'literature_review', label: 'Review', icon: BookOpen, description: 'Synthesizes literature and themes.' },
  { id: 'citation_verification', label: 'Citations', icon: CheckCircle2, description: 'Validates DOIs and contextual links.' },
  { id: 'gap_analysis', label: 'Gap Analysis', icon: HelpCircle, description: 'Finds research gaps and open ideas.' },
  { id: 'methodology_suggestion', label: 'Methodology', icon: Cpu, description: 'Compares and recommends methods.' },
  { id: 'draft_writing', label: 'Drafting', icon: Edit3, description: 'Generates outline and draft sections.' },
  { id: 'hallucination_detection', label: 'Verification', icon: AlertTriangle, description: 'Cross-checks drafts with source chunks.' },
  { id: 'formatting', label: 'Formatting', icon: FileText, description: 'Formats draft into IEEE/ACM style.' },
  { id: 'journal_recommendation', label: 'Journals', icon: Book, description: 'Recommends high-fit venues.' },
  { id: 'reviewer_simulation', label: 'Peer Review', icon: Users, description: 'Evaluates draft with simulated reviewers.' },
  { id: 'submission_preparation', label: 'Submission', icon: Mail, description: 'Prepares submission letter and checklists.' },
];

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rs = s % 60;
  if (m < 60) return `${m}m ${rs}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

function WorkflowGraph({ currentAgent, status, progressPct = 0, startedAt }: WorkflowGraphProps) {
  const [elapsed, setElapsed] = useState('—');

  // Elapsed time ticker — freezes on terminal status
  useEffect(() => {
    if (!startedAt) return;
    const start = new Date(startedAt).getTime();
    const tick = () => setElapsed(formatElapsed(Date.now() - start));
    tick();
    if (status === 'completed' || status === 'failed' || status === 'cancelled') return;
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt, status]);

  const getNodeStatus = (nodeId: string): 'idle' | 'running' | 'completed' | 'failed' => {
    if (status === 'completed') return 'completed';
    if (status === 'failed' && currentAgent === nodeId) return 'failed';
    if (currentAgent === nodeId && (status === 'running' || status === 'in_progress')) return 'running';
    const ids = NODES.map(n => n.id);
    const ci = currentAgent ? ids.indexOf(currentAgent) : -1;
    const ni = ids.indexOf(nodeId);
    if (ci !== -1 && ni < ci) return 'completed';
    return 'idle';
  };

  const completedCount = NODES.filter(n => getNodeStatus(n.id) === 'completed').length;
  const isRunning = status === 'running' || status === 'in_progress';
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';
  const isIdle = !status || status === 'idle';

  const effectiveProgress = progressPct > 0
    ? progressPct
    : isCompleted ? 100
    : NODES.length > 0 ? (completedCount / NODES.length) * 100
    : 0;

  const sc = isFailed
    ? { label: 'Failed', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-red-500' }
    : isCompleted
    ? { label: 'Completed', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', dot: 'bg-emerald-500' }
    : isRunning
    ? { label: 'Running', color: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200', dot: 'bg-indigo-500' }
    : { label: 'Idle', color: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-200', dot: 'bg-gray-400' };

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* ── Header ── */}
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-sm">
              <Cpu className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Agent Pipeline</h3>
              <p className="text-[11px] text-gray-400">{NODES.length} agents · {completedCount} completed</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Elapsed */}
            {startedAt && (
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-gray-50 border border-gray-100">
                <Clock className="w-3 h-3 text-gray-400" />
                <span className="text-[11px] font-mono tabular-nums text-gray-600">{elapsed}</span>
              </div>
            )}
            {/* Current agent */}
            {isRunning && currentAgent && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 capitalize">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-indigo-600" />
                </span>
                {currentAgent.replace(/_/g, ' ')}
              </span>
            )}
            {/* Status */}
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${sc.bg} ${sc.color} ${sc.border}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${sc.dot} ${isRunning ? 'animate-pulse' : ''}`} />
              {sc.label}
            </span>
          </div>
        </div>

        {/* Progress bar */}
        {!isIdle && (
          <div className="mt-3 space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-gray-500 font-medium">{completedCount} of {NODES.length} agents</span>
              <span className="font-semibold text-indigo-600 tabular-nums font-mono">{Math.round(effectiveProgress)}%</span>
            </div>
            <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ease-out ${
                  isCompleted ? 'bg-emerald-500'
                  : isFailed ? 'bg-red-500'
                  : 'bg-gradient-to-r from-indigo-500 to-violet-500'
                } ${isRunning ? 'animate-pulse-slow' : ''}`}
                style={{ width: `${effectiveProgress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Agent Grid ── */}
      <div className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {NODES.map((node, idx) => {
            const ns = getNodeStatus(node.id);
            const Icon = node.icon;

            return (
              <div
                key={node.id}
                className={`relative p-3 rounded-lg border transition-all duration-300 ${
                  ns === 'running'
                    ? 'border-indigo-200 bg-indigo-50/80 ring-1 ring-indigo-100 shadow-sm'
                    : ns === 'completed'
                    ? 'border-emerald-200 bg-emerald-50/50'
                    : ns === 'failed'
                    ? 'border-red-200 bg-red-50/50'
                    : 'border-gray-100 bg-gray-50/30'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 ${
                      ns === 'running' ? 'bg-indigo-100'
                      : ns === 'completed' ? 'bg-emerald-100'
                      : ns === 'failed' ? 'bg-red-100'
                      : 'bg-gray-100'
                    }`}>
                      <Icon className={`w-3.5 h-3.5 ${
                        ns === 'running' ? 'text-indigo-600'
                        : ns === 'completed' ? 'text-emerald-600'
                        : ns === 'failed' ? 'text-red-500'
                        : 'text-gray-400'
                      }`} />
                    </div>
                    <span className={`text-xs font-semibold truncate ${
                      ns === 'running' ? 'text-indigo-900'
                      : ns === 'completed' ? 'text-gray-700'
                      : ns === 'failed' ? 'text-red-800'
                      : 'text-gray-400'
                    }`}>
                      {node.label}
                    </span>
                  </div>

                  <div className="shrink-0">
                    {ns === 'running' && <Loader2 className="w-3.5 h-3.5 text-indigo-500 animate-spin" />}
                    {ns === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
                    {ns === 'failed' && <XCircle className="w-3.5 h-3.5 text-red-500" />}
                  </div>
                </div>

                <p className={`text-[10px] leading-relaxed line-clamp-2 ${
                  ns === 'idle' ? 'text-gray-400'
                  : ns === 'running' ? 'text-indigo-600/80'
                  : ns === 'completed' ? 'text-emerald-700/60'
                  : 'text-red-600/70'
                }`}>
                  {node.description}
                </p>

                <span className={`absolute bottom-2 right-2.5 text-[9px] font-mono tabular-nums ${
                  ns === 'idle' ? 'text-gray-200' : 'text-gray-300'
                }`}>
                  {String(idx + 1).padStart(2, '0')}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default memo(WorkflowGraph);
