'use client';

import React, { useEffect, useMemo } from 'react';
import AppShell from '@/components/layout/AppShell';
import { useProjectStore } from '@/stores/projectStore';
import { useAgentStore } from '@/stores/agentStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import WorkflowTimeline from '@/components/research/WorkflowTimeline';
import StreamingContent from '@/components/research/StreamingContent';
import ResearchResults from '@/components/research/ResearchResults';
import ResearchArtifactViewer from '@/components/research/ResearchArtifactViewer';
import WorkflowAnalyticsDashboard from '@/components/research/WorkflowAnalyticsDashboard';
import AgentHistoryViewer from '@/components/research/AgentHistoryViewer';
import ResearchCopilot from '@/components/research/ResearchCopilot';
import { getWorkflowState } from '@/types';
import { useSSE } from '@/hooks/useSSE';
import {
  Beaker,
  Play,
  Pause,
  ChevronRight,
  AlertTriangle,
  FileText,
  Loader2,
  FolderOpen,
} from 'lucide-react';
import Link from 'next/link';

interface ProjectOverviewProps {
  params: Promise<{ id: string }>;
}

export default function ProjectOverview({ params }: ProjectOverviewProps) {
  const { id } = React.use(params);
  const { currentProject, fetchProject, isLoading } = useProjectStore();
  const { researchStatus, fetchResearchStatus, startResearch, pauseResearch, resumeResearch, cancelResearch, agentLogs, streamingContent } = useAgentStore();

  const isWorkflowActive = researchStatus != null && (researchStatus.status === 'running' || researchStatus.status === 'paused');

  const workflowState = useMemo(
    () => getWorkflowState(currentProject),
    [currentProject]
  );

  useWebSocket(id);
  useSSE(isWorkflowActive ? id : null);

  useEffect(() => {
    fetchProject(id);
    fetchResearchStatus(id);
  }, [id, fetchProject, fetchResearchStatus]);

  const handleStartWorkflow = async () => {
    if (!currentProject) return;
    try {
      await startResearch(id, {
        max_papers: 15,
        format_style: currentProject.settings_json?.format_style || 'ieee',
      });
    } catch (err) {
      console.error(err);
    }
  };

  const progressPct = researchStatus?.progress_pct || 0;

  // ─── Loading skeleton ──────────────────────────────────────────────
  if (isLoading || !currentProject) {
    return (
      <AppShell>
        <div className="space-y-6">
          <div className="space-y-2">
            <div className="skeleton h-3 w-28" />
            <div className="skeleton h-7 w-72" />
          </div>
          <div className="skeleton h-28 w-full rounded-lg" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="skeleton h-40 w-full rounded-lg" />
            </div>
            <div className="skeleton h-64 w-full rounded-lg" />
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6 select-none">
        {/* Breadcrumb / Title */}
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 uppercase tracking-wide">
            <Link href="/" className="hover:text-gray-600 transition-colors">Projects</Link>
            <ChevronRight className="w-3 h-3" />
            <span className="text-gray-500">Overview</span>
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">{currentProject.title}</h1>
        </div>

        {/* Action Panel */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1 max-w-xl">
              <h3 className="font-medium text-sm text-gray-900 flex items-center gap-1.5">
                <Beaker className="w-4 h-4 text-indigo-600" />
                Workflow Control
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Launch the multi-agent pipeline to retrieve papers, analyze gaps, write drafts, and verify citations.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              {researchStatus?.status === 'running' && (
                <button
                  onClick={() => pauseResearch(id)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-md text-sm font-medium transition-colors"
                >
                  <Pause className="w-3.5 h-3.5" />
                  Pause
                </button>
              )}

              {researchStatus?.status === 'paused' && (
                <button
                  onClick={() => resumeResearch(id)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-medium transition-colors"
                >
                  <Play className="w-3.5 h-3.5" />
                  Resume
                </button>
              )}

              {!isWorkflowActive && (
                <button
                  onClick={handleStartWorkflow}
                  className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-medium shadow-sm transition-colors"
                >
                  <Play className="w-3.5 h-3.5" />
                  Start Workflow
                </button>
              )}

              {isWorkflowActive && (
                <button
                  onClick={() => cancelResearch(id)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-white border border-red-200 text-red-600 hover:bg-red-50 rounded-md text-sm font-medium transition-colors"
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Cancel
                </button>
              )}
            </div>
          </div>

          {/* Progress bar inside action panel when running */}
          {researchStatus?.status === 'running' && (
            <div className="px-5 pb-4">
              <div className="flex justify-between text-[11px] mb-1">
                <span className="text-gray-500 font-medium flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin text-indigo-500" />
                  {researchStatus.current_agent?.replace(/_/g, ' ') || 'Processing...'}
                </span>
                <span className="font-semibold text-indigo-600 font-mono tabular-nums">
                  {Math.round(progressPct)}%
                </span>
              </div>
              <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-700 ease-out animate-pulse-slow"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Research Parameters */}
            <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide">
                Research Parameters
              </h3>
              <div className="space-y-4 select-text">
                <div className="space-y-1">
                  <h4 className="text-xs font-medium text-gray-500">Research Topic</h4>
                  <p className="text-sm text-gray-700 leading-relaxed">{currentProject.topic || 'No topic details provided.'}</p>
                </div>
                {currentProject.description && (
                  <div className="space-y-1">
                    <h4 className="text-xs font-medium text-gray-500">Background Notes</h4>
                    <p className="text-sm text-gray-700 leading-relaxed">{currentProject.description}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Live Streaming Content */}
            {isWorkflowActive && Object.keys(streamingContent).length > 0 && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-600" />
                  <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">Live Draft Output</span>
                </div>
                <div className="p-5">
                  <StreamingContent
                    content={streamingContent}
                    activeAgent={researchStatus?.current_agent}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Right Column */}
          <div className="lg:col-span-1 space-y-6">
            {/* Workspace Status */}
            <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide">
                Status
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-500">Workflow</span>
                  <span className="font-medium text-gray-900 capitalize">
                    {researchStatus?.status || 'Idle'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-500">Active Agent</span>
                  <span className="font-medium text-indigo-600 capitalize">
                    {researchStatus?.current_agent?.replace(/_/g, ' ') || '—'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-500">Format</span>
                  <span className="font-medium text-gray-900 uppercase">
                    {currentProject.settings_json?.format_style || 'IEEE'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-500">Created</span>
                  <span className="font-medium text-gray-900">
                    {new Date(currentProject.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Workflow Timeline */}
            <WorkflowTimeline
              logs={agentLogs}
              activeAgent={researchStatus?.current_agent || null}
              workflowStatus={researchStatus?.status || null}
            />

            {/* Workflow Analytics */}
            {workflowState && (
              <WorkflowAnalyticsDashboard workflowState={workflowState} />
            )}
          </div>
        </div>

        {/* Phase 2: Research Results */}
        {workflowState && (
          <div className="space-y-6">
            <ResearchResults workflowState={workflowState} />
            <ResearchArtifactViewer workflowState={workflowState} />
          </div>
        )}

        {/* Copilot */}
        <ResearchCopilot
          projectId={id}
          hasWorkflowResults={workflowState !== null}
        />

        {/* Agent History */}
        {workflowState && (
          <AgentHistoryViewer
            history={workflowState.agent_history ?? []}
            errors={workflowState.errors ?? []}
          />
        )}
      </div>
    </AppShell>
  );
}
