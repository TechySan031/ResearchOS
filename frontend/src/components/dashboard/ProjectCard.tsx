'use client';

import Link from 'next/link';
import { Project } from '@/types';
import {
  ArrowRight,
  Trash2,
  Clock,
  Compass,
} from 'lucide-react';

interface ProjectCardProps {
  project: Project;
  onDelete: (id: string) => void;
}

export default function ProjectCard({
  project,
  onDelete,
}: ProjectCardProps) {
  const statusStyles: Record<string, string> = {
    created: 'bg-gray-100 text-gray-600',
    researching: 'bg-blue-50 text-blue-700',
    drafting: 'bg-indigo-50 text-indigo-700',
    reviewing: 'bg-amber-50 text-amber-700',
    completed: 'bg-emerald-50 text-emerald-700',
    failed: 'bg-red-50 text-red-700',
  };

  const statusLabel: Record<string, string> = {
    created: 'Initialized',
    researching: 'Retrieving Papers',
    drafting: 'Writing Draft',
    reviewing: 'Review',
    completed: 'Publication Ready',
    failed: 'Failed',
  };

  const formattedDate = new Date(project.created_at).toLocaleDateString(
    'en-US',
    {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }
  );

  return (
    <div className="group bg-white border border-gray-200 rounded-xl p-6 flex flex-col h-[320px] transition-all duration-200 hover:shadow-lg hover:-translate-y-1 hover:border-indigo-200">

      {/* Header */}
      <div className="flex items-center justify-between">

        <span
          className={`px-3 py-1 rounded-full text-xs font-medium ${statusStyles[project.status]}`}
        >
          {statusLabel[project.status]}
        </span>

        <button
          onClick={() => onDelete(project.id)}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-500"
        >
          <Trash2 size={17} />
        </button>

      </div>

      {/* Title */}
      <h2 className="mt-5 text-xl font-semibold text-gray-900 line-clamp-2">
        {project.title}
      </h2>

      {/* Topic */}
      <div className="flex gap-2 mt-4 text-gray-500 text-sm">

        <Compass
          size={16}
          className="mt-1 shrink-0"
        />

        <p
          className="leading-7"
          style={{
            display: "-webkit-box",
            WebkitLineClamp: 4,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {project.topic || "No topic description provided."}
        </p>

      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer */}
      <div className="border-t border-gray-100 pt-4 flex items-center justify-between">

        <div className="flex items-center gap-2 text-xs text-gray-400">

          <Clock size={15} />

          {formattedDate}

        </div>

        <Link
          href={`/project/${project.id}`}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-all"
        >
          Open Project

          <ArrowRight
            size={16}
            className="group-hover:translate-x-1 transition-transform"
          />

        </Link>

      </div>

    </div>
  );
}