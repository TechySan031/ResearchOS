'use client';

import React from 'react';
import { WorkflowState } from '@/types';
import ProjectResultsTabs from './ProjectResultsTabs';
import {
    BookOpen,
    FileSearch,
    Lightbulb,
    CheckCircle2,
    AlertCircle,
    Loader2,
} from 'lucide-react';

interface ResearchResultsProps {
    workflowState: WorkflowState;
}

/**
 * Top-level results container for a completed or in-progress research workflow.
 *
 * Renders a summary header with key metrics derived from workflow_state,
 * followed by a tabbed interface for browsing all workflow outputs.
 */
export default function ResearchResults({ workflowState }: ResearchResultsProps) {
    const paperCount = workflowState.retrieved_papers?.length ?? 0;
    const gapCount = workflowState.research_gaps?.length ?? 0;
    const themeCount = workflowState.key_themes?.length ?? 0;
    const isCompleted = workflowState.status === 'completed';
    const isFailed = workflowState.status === 'failed';
    const isRunning = workflowState.status === 'running' || workflowState.status === 'in_progress';

    const statusConfig = isFailed
        ? { icon: AlertCircle, label: 'Failed', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' }
        : isCompleted
            ? { icon: CheckCircle2, label: 'Completed', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' }
            : isRunning
                ? { icon: Loader2, label: 'Running', color: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200' }
                : { icon: AlertCircle, label: workflowState.status || 'Unknown', color: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-200' };

    const StatusIcon = statusConfig.icon;

    return (
        <div className="space-y-6">
            {/* ── Summary Header ── */}
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="px-6 py-5 space-y-4">
                    {/* Title row */}
                    <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1 min-w-0">
                            <h2 className="text-lg font-semibold text-gray-900 tracking-tight">
                                Research Results
                            </h2>
                            {workflowState.topic && (
                                <p className="text-sm text-gray-500 leading-relaxed truncate max-w-xl">
                                    {workflowState.topic}
                                </p>
                            )}
                        </div>

                        {/* Status badge */}
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border shrink-0 ${statusConfig.bg} ${statusConfig.color} ${statusConfig.border}`}>
                            <StatusIcon className={`w-3 h-3 ${isRunning ? 'animate-spin' : ''}`} />
                            {statusConfig.label}
                        </span>
                    </div>

                    {/* Metric pills */}
                    <div className="flex flex-wrap gap-3">
                        <MetricPill
                            icon={BookOpen}
                            label="Papers"
                            value={paperCount}
                            color="indigo"
                        />
                        <MetricPill
                            icon={Lightbulb}
                            label="Themes"
                            value={themeCount}
                            color="violet"
                        />
                        <MetricPill
                            icon={FileSearch}
                            label="Gaps"
                            value={gapCount}
                            color="amber"
                        />
                        {workflowState.revision_count != null && (
                            <MetricPill
                                icon={CheckCircle2}
                                label="Revisions"
                                value={`${workflowState.revision_count}/${workflowState.max_revisions ?? '∞'}`}
                                color="emerald"
                            />
                        )}
                    </div>

                    {/* Key themes chips */}
                    {workflowState.key_themes?.length > 0 && (
                        <div className="space-y-2">
                            <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
                                Key Themes
                            </h4>
                            <div className="flex flex-wrap gap-2">
                                {workflowState.key_themes.map((theme, idx) => (
                                    <span
                                        key={idx}
                                        className="inline-flex items-center px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 text-xs font-medium border border-indigo-100"
                                    >
                                        {theme}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Tabbed Results ── */}
            <ProjectResultsTabs workflowState={workflowState} />
        </div>
    );
}

// ─── Internal MetricPill component ─────────────────────────────────────

interface MetricPillProps {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    value: number | string;
    color: 'indigo' | 'violet' | 'amber' | 'emerald';
}

const colorMap = {
    indigo: { bg: 'bg-indigo-50', text: 'text-indigo-700', icon: 'text-indigo-500' },
    violet: { bg: 'bg-violet-50', text: 'text-violet-700', icon: 'text-violet-500' },
    amber: { bg: 'bg-amber-50', text: 'text-amber-700', icon: 'text-amber-500' },
    emerald: { bg: 'bg-emerald-50', text: 'text-emerald-700', icon: 'text-emerald-500' },
} as const;

function MetricPill({ icon: Icon, label, value, color }: MetricPillProps) {
    const colors = colorMap[color];
    return (
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg ${colors.bg}`}>
            <Icon className={`w-3.5 h-3.5 ${colors.icon}`} />
            <span className={`text-xs font-semibold tabular-nums ${colors.text}`}>{value}</span>
            <span className="text-xs text-gray-500">{label}</span>
        </div>
    );
}
