'use client';

import React, { useEffect, useMemo } from 'react';
import AppShell from '@/components/layout/AppShell';
import RichEditor from '@/components/editor/RichEditor';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useProjectStore } from '@/stores/projectStore';
import { getWorkflowState } from '@/types';
import { FileText, ChevronRight } from 'lucide-react';
import Link from 'next/link';

interface DraftEditorProps {
  params: Promise<{ id: string }>;
}

export default function DraftEditor({ params }: DraftEditorProps) {
  const { id } = React.use(params);
  const { currentProject, fetchProject } = useProjectStore();

  useWebSocket(id);

  useEffect(() => {
    fetchProject(id);
  }, [id, fetchProject]);

  const workflowState = useMemo(
    () => getWorkflowState(currentProject),
    [currentProject]
  );

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Breadcrumbs */}
        <div className="space-y-1 select-none">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 uppercase tracking-wide">
            <Link href="/" className="hover:text-gray-600 transition-colors">Projects</Link>
            <ChevronRight className="w-3 h-3" />
            {currentProject && (
              <Link href={`/project/${id}`} className="hover:text-gray-600 transition-colors truncate max-w-[150px]">
                {currentProject.title}
              </Link>
            )}
            <ChevronRight className="w-3 h-3" />
            <span className="text-gray-500">Draft Editor</span>
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-600" />
            Draft Workspace Editor
          </h1>
        </div>

        {/* Editor component — with formatted paper fallback */}
        <RichEditor
          projectId={id}
          formattedPaper={workflowState?.formatted_paper}
        />
      </div>
    </AppShell>
  );
}
