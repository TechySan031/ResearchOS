'use client';

import React, { useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import WorkflowGraph from '@/components/research/WorkflowGraph';
import AgentTimeline from '@/components/research/AgentTimeline';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgentStore } from '@/stores/agentStore';
import { useProjectStore } from '@/stores/projectStore';
import { Cpu, ChevronRight } from 'lucide-react';
import Link from 'next/link';

interface ResearchWorkflowProps {
  params: Promise<{ id: string }>;
}

export default function ResearchWorkflow({ params }: ResearchWorkflowProps) {
  const { id } = React.use(params);
  const { currentProject, fetchProject } = useProjectStore();
  const {
    researchStatus,
    agentLogs,
    fetchResearchStatus,
    fetchAgentLogs,
  } = useAgentStore();

  useWebSocket(id);

  useEffect(() => {
    fetchProject(id);
    fetchResearchStatus(id);
    fetchAgentLogs(id);
  }, [id, fetchProject, fetchResearchStatus, fetchAgentLogs]);

  const currentAgent = researchStatus?.current_agent || null;
  const status = researchStatus?.status || 'idle';
  const progressPct = researchStatus?.progress_pct || 0;

  return (
    <AppShell>
      <div className="space-y-6 select-none">
        {/* Breadcrumbs */}
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 uppercase tracking-wide">
            <Link href="/" className="hover:text-gray-600 transition-colors">Projects</Link>
            <ChevronRight className="w-3 h-3" />
            {currentProject && (
              <Link href={`/project/${id}`} className="hover:text-gray-600 transition-colors truncate max-w-[150px]">
                {currentProject.title}
              </Link>
            )}
            <ChevronRight className="w-3 h-3" />
            <span className="text-gray-500">Workflow</span>
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <Cpu className="w-6 h-6 text-indigo-600" />
            Agent Workflow Console
          </h1>
        </div>

        {/* Workflow Graph — now contains its own progress bar, elapsed time, status badges */}
        <WorkflowGraph
          currentAgent={currentAgent}
          status={status}
          progressPct={progressPct}
          startedAt={researchStatus?.started_at}
        />

        {/* Agent Event Log */}
        <AgentTimeline logs={agentLogs} />
      </div>
    </AppShell>
  );
}
