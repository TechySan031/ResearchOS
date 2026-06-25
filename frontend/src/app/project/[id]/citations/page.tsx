'use client';

import React, { useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import CitationList from '@/components/citations/CitationList';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useProjectStore } from '@/stores/projectStore';
import { BookOpen, ChevronRight } from 'lucide-react';
import Link from 'next/link';

interface CitationsManagerProps {
  params: Promise<{ id: string }>;
}

export default function CitationsManager({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const { currentProject, fetchProject } = useProjectStore();

  useWebSocket(id);

  useEffect(() => {
    fetchProject(id);
  }, [id, fetchProject]);

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Breadcrumbs */}
        <div className="space-y-1 select-none">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
            <Link href="/" className="hover:text-zinc-300">Workspaces</Link>
            <ChevronRight className="w-3 h-3 text-zinc-600" />
            {currentProject && (
              <Link href={`/project/${id}`} className="hover:text-zinc-300 truncate max-w-[150px]">{currentProject.title}</Link>
            )}
            <ChevronRight className="w-3 h-3 text-zinc-600" />
            <span className="text-zinc-400">Citations & RAG</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-violet-500" />
            Citations & RAG Ingestion
          </h1>
        </div>

        {/* Citations panel */}
        <CitationList projectId={id} />
      </div>
    </AppShell>
  );
}
