'use client';

import React, { useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import CitationList from '@/components/citations/CitationList';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useProjectStore } from '@/stores/projectStore';
import { BookOpen, ChevronRight } from 'lucide-react';
import Link from 'next/link';

export default function CitationsManager({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const { currentProject, fetchProject } = useProjectStore();

  useWebSocket(id);

  useEffect(() => {
    fetchProject(id);
  }, [id, fetchProject]);

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
            <span className="text-gray-500">Citations & RAG</span>
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-indigo-600" />
            Citations & RAG Ingestion
          </h1>
        </div>

        {/* Citations panel */}
        <CitationList projectId={id} />
      </div>
    </AppShell>
  );
}
