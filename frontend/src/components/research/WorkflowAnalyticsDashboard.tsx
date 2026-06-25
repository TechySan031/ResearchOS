'use client';

import React from 'react';
import { WorkflowState } from '@/types';
import { useAgentStore } from '@/stores/agentStore';
import {
  BookOpen,
  Database,
  FileSearch,
  ShieldCheck,
  RefreshCw,
  Activity,
  User,
  Clock,
  CheckCircle2,
  Layers,
  Timer,
  Zap,
} from 'lucide-react';

interface WorkflowAnalyticsDashboardProps {
  workflowState: WorkflowState;
}

/**
 * Analytics dashboard showing workflow metrics derived from workflow_state.
 *
 * Extends the MetricCard pattern used in the existing codebase but with
 * a richer grid layout, gradient accents, and more metrics.
 */
export default function WorkflowAnalyticsDashboard({ workflowState }: WorkflowAnalyticsDashboardProps) {
  const storeMetrics = useAgentStore((s) => s.metrics);

  const completedAgents = workflowState.agent_history?.filter((a) => a.status === 'completed') ?? [];
  const totalAgents = workflowState.agent_history?.length ?? 0;

  const totalElapsedSeconds = workflowState.agent_history?.reduce(
    (sum, entry) => sum + (entry.elapsed_seconds ?? 0),
    0
  ) ?? 0;

  const papersCount = workflowState.retrieved_papers?.length ?? 0;
  const gapsCount = workflowState.research_gaps?.length ?? 0;
  const citationsVerified = workflowState.citation_verification_results?.length ?? 0;
  const sectionsCount = Object.keys(workflowState.paper_sections ?? {}).length;

  const metrics: MetricItem[] = [
    {
      label: 'Papers Retrieved',
      value: papersCount,
      icon: BookOpen,
      gradient: 'from-indigo-500 to-indigo-600',
      lightBg: 'bg-indigo-50',
      lightText: 'text-indigo-700',
    },
    {
      label: 'Embeddings Stored',
      value: workflowState.paper_embeddings_stored ? 'Yes' : 'No',
      icon: Database,
      gradient: 'from-violet-500 to-violet-600',
      lightBg: 'bg-violet-50',
      lightText: 'text-violet-700',
    },
    {
      label: 'Research Gaps',
      value: gapsCount,
      icon: FileSearch,
      gradient: 'from-amber-500 to-amber-600',
      lightBg: 'bg-amber-50',
      lightText: 'text-amber-700',
    },
    {
      label: 'Citations Verified',
      value: citationsVerified,
      icon: ShieldCheck,
      gradient: 'from-cyan-500 to-cyan-600',
      lightBg: 'bg-cyan-50',
      lightText: 'text-cyan-700',
    },
    {
      label: 'Draft Sections',
      value: sectionsCount,
      icon: Layers,
      gradient: 'from-teal-500 to-teal-600',
      lightBg: 'bg-teal-50',
      lightText: 'text-teal-700',
    },
    {
      label: 'Revisions',
      value: `${workflowState.revision_count ?? 0} / ${workflowState.max_revisions ?? '∞'}`,
      icon: RefreshCw,
      gradient: 'from-rose-500 to-rose-600',
      lightBg: 'bg-rose-50',
      lightText: 'text-rose-700',
    },
    {
      label: 'Agent Steps',
      value: `${completedAgents.length} / ${totalAgents}`,
      icon: CheckCircle2,
      gradient: 'from-emerald-500 to-emerald-600',
      lightBg: 'bg-emerald-50',
      lightText: 'text-emerald-700',
    },
    {
      label: 'Current Agent',
      value: workflowState.current_agent
        ? workflowState.current_agent.replace(/_/g, ' ')
        : '—',
      icon: User,
      gradient: 'from-sky-500 to-sky-600',
      lightBg: 'bg-sky-50',
      lightText: 'text-sky-700',
      capitalize: true,
    },
    {
      label: 'Total Elapsed',
      value: totalElapsedSeconds > 0 ? formatDuration(totalElapsedSeconds) : '—',
      icon: Clock,
      gradient: 'from-orange-500 to-orange-600',
      lightBg: 'bg-orange-50',
      lightText: 'text-orange-700',
    },
    {
      label: 'Status',
      value: workflowState.status || '—',
      icon: Activity,
      gradient: 'from-purple-500 to-purple-600',
      lightBg: 'bg-purple-50',
      lightText: 'text-purple-700',
      capitalize: true,
    },
  ];

  // Add real-time metrics from the agent store (TTFT / workflow duration)
  if (storeMetrics.ttftMs != null) {
    metrics.push({
      label: 'Time to First Token',
      value: `${storeMetrics.ttftMs.toFixed(0)}ms`,
      icon: Zap,
      gradient: 'from-yellow-500 to-yellow-600',
      lightBg: 'bg-yellow-50',
      lightText: 'text-yellow-700',
    });
  }
  if (storeMetrics.workflowDurationMs != null) {
    metrics.push({
      label: 'Workflow Duration',
      value: formatDuration(storeMetrics.workflowDurationMs / 1000),
      icon: Timer,
      gradient: 'from-fuchsia-500 to-fuchsia-600',
      lightBg: 'bg-fuchsia-50',
      lightText: 'text-fuchsia-700',
    });
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
          <Activity className="w-3 h-3" />
          Workflow Analytics
        </h3>
      </div>

      <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-2 gap-2">
        {metrics.map((metric) => (
          <DashboardCard key={metric.label} metric={metric} />
        ))}
      </div>
    </div>
  );
}

// ─── Internal Types & Components ──────────────────────────────────────

interface MetricItem {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  gradient: string;
  lightBg: string;
  lightText: string;
  capitalize?: boolean;
}

function DashboardCard({ metric }: { metric: MetricItem }) {
  const Icon = metric.icon;
  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg ${metric.lightBg} transition-colors`}>
      <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${metric.gradient} flex items-center justify-center shrink-0 shadow-sm`}>
        <Icon className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="min-w-0">
        <p className={`text-sm font-semibold tabular-nums ${metric.lightText} ${metric.capitalize ? 'capitalize' : ''} truncate`}>
          {metric.value}
        </p>
        <p className="text-[11px] text-gray-500 truncate">{metric.label}</p>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return `${mins}m ${secs}s`;
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return `${hrs}h ${remainMins}m`;
}
