'use client';

import React from 'react';
import Link from 'next/link';
import { Project } from '@/types';
import { 
  ArrowRight, 
  Trash2, 
  Clock,
  Compass
} from 'lucide-react';

interface ProjectCardProps {
  project: Project;
  onDelete: (id: string) => void;
}

export default function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const statusStyles: Record<string, string> = {
    created: 'bg-gray-100 text-gray-600 border-gray-200',
    researching: 'bg-blue-50 text-blue-700 border-blue-200',
    drafting: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    reviewing: 'bg-amber-50 text-amber-700 border-amber-200',
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    failed: 'bg-red-50 text-red-700 border-red-200',
  };

  const statusLabel: Record<string, string> = {
    created: 'Initialized',
    researching: 'Retrieving Papers',
    drafting: 'Writing Draft',
    reviewing: 'Simulating Review',
    completed: 'Publication Ready',
    failed: 'Failed',
  };

  const formattedDate = new Date(project.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 flex flex-col justify-between h-52 relative overflow-hidden group hover:shadow-md hover:border-gray-300 transition-all duration-200">
      <div className="space-y-3">
        {/* Top bar with Badge and Delete Button */}
        <div className="flex items-center justify-between">
          <span className={`px-2 py-0.5 rounded-md text-[11px] font-medium border ${statusStyles[project.status] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
            {statusLabel[project.status] || project.status}
          </span>
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDelete(project.id);
            }}
            className="p-1.5 rounded-md text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
            title="Delete Project"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-gray-900 text-base line-clamp-1 group-hover:text-indigo-600 transition-colors">
          {project.title}
        </h3>

        {/* Topic */}
        <div className="flex items-start gap-1.5 text-sm text-gray-500 line-clamp-2">
          <Compass className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
          <span className="leading-relaxed">{project.topic || 'No topic description provided.'}</span>
        </div>
      </div>

      {/* Footer stats and link */}
      <div className="border-t border-gray-100 pt-3 flex items-center justify-between mt-auto">
        <div className="flex items-center gap-1 text-[11px] text-gray-400 font-medium">
          <Clock className="w-3.5 h-3.5" />
          <span>{formattedDate}</span>
        </div>

        <Link
          href={`/project/${project.id}`}
          className="flex items-center gap-1 text-sm font-medium text-indigo-600 group-hover:text-indigo-700 transition-colors"
        >
          Open
          <ArrowRight className="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform" />
        </Link>
      </div>
    </div>
  );
}
