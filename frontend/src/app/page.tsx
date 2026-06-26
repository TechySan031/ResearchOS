'use client';

import React, { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import MetricCard from '@/components/MetricCard';
import ProjectCard from '@/components/dashboard/ProjectCard';
import { useProjectStore } from '@/stores/projectStore';
import { useAuthStore } from '@/stores/authStore';
import { useToast } from '@/components/Toast';
import {
  Plus,
  Beaker,
  FolderPlus,
  Sparkles,
  X,
  Loader2,
} from 'lucide-react';

export default function Dashboard() {
  const { projects, isLoading, fetchProjects, createProject, deleteProject } = useProjectStore();
  const { showToast } = useToast();
  const [showModal, setShowModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // New Project Fields
  const [title, setTitle] = useState('');
  const [topic, setTopic] = useState('');
  const [description, setDescription] = useState('');
  const [formatStyle, setFormatStyle] = useState('ieee');

  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      fetchProjects();
    }
  }, [isAuthenticated, fetchProjects]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsCreating(true);
    try {
      await createProject({
        title,
        topic,
        description,
        settings: { format_style: formatStyle },
      });

      // Reset form
      setTitle('');
      setTopic('');
      setDescription('');
      setShowModal(false);
      showToast('Project created successfully', 'success');
      fetchProjects();
    } catch (err: any) {
      const msg = err.info?.detail || err.message || 'Failed to create project';
      showToast(msg, 'error');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this project? All papers, citations, and drafts will be deleted.')) {
      try {
        await deleteProject(id);
        showToast('Project deleted', 'info');
      } catch {
        showToast('Failed to delete project', 'error');
      }
    }
  };

  // Stats calculation
  const totalProjects = projects.length;
  const researchingCount = projects.filter((p) => p.status === 'researching').length;
  const completedCount = projects.filter((p) => p.status === 'completed').length;
  const draftingCount = projects.filter((p) => p.status === 'drafting').length;

  return (
    <AppShell>
      <div className="space-y-6 select-none">
        {/* Page title and action bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-gray-900 flex items-center gap-2">
              <Beaker className="w-6 h-6 text-indigo-600" />
              Research Workspace
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Manage your AI-assisted research paper projects.
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-medium shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Project
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">Total Projects</p>
            <h3 className="text-xl font-semibold text-gray-900 mt-1">{totalProjects}</h3>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">In Retrieval</p>
            <h3 className="text-xl font-semibold text-blue-600 mt-1">{researchingCount}</h3>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">In Drafting</p>
            <h3 className="text-xl font-semibold text-indigo-600 mt-1">{draftingCount}</h3>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">Publication Ready</p>
            <h3 className="text-xl font-semibold text-emerald-600 mt-1">{completedCount}</h3>
          </div>
        </div>

        {/* Workflow Observability */}
        <div className="grid grid-cols-1">
          <MetricCard />
        </div>

        {/* Project List */}
        {isLoading && projects.length === 0 ? (
          /* Skeleton loader cards */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-5 h-52 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="skeleton h-5 w-24" />
                  <div className="skeleton h-5 w-5 rounded" />
                </div>
                <div className="skeleton h-5 w-3/4" />
                <div className="space-y-2">
                  <div className="skeleton h-3 w-full" />
                  <div className="skeleton h-3 w-2/3" />
                </div>
                <div className="flex items-center justify-between mt-auto pt-4">
                  <div className="skeleton h-3 w-20" />
                  <div className="skeleton h-4 w-12" />
                </div>
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-12 text-center flex flex-col items-center justify-center gap-4">
            <FolderPlus className="w-10 h-10 text-gray-300" />
            <div>
              <h3 className="font-semibold text-gray-900 text-sm">No research projects yet</h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                Create a project and enter a research topic to start the multi-agent research workflow.
              </p>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-md text-sm font-medium transition-colors"
            >
              Get Started
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}

        {/* New Project Modal */}
        {showModal && (
          <div className="fixed inset-0 bg-black/20 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
            <div className="bg-white w-full max-w-lg rounded-xl border border-gray-200 overflow-hidden shadow-xl flex flex-col">
              {/* Modal Header */}
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                <span className="font-semibold text-sm text-gray-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  New Research Project
                </span>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Modal Body */}
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Project Title</label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Deep Learning in Quantum Computing"
                    className="w-full bg-white border border-gray-300 px-3 py-2 text-sm rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Research Topic</label>
                  <textarea
                    required
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Describe the topic the agents should research, retrieve papers for, and draft about..."
                    className="w-full bg-white border border-gray-300 px-3 py-2 text-sm rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 min-h-[80px] transition-shadow"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    Description <span className="text-gray-300 normal-case">(optional)</span>
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Additional notes or background information..."
                    className="w-full bg-white border border-gray-300 px-3 py-2 text-sm rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 min-h-[60px] transition-shadow"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Citation Format</label>
                  <select
                    value={formatStyle}
                    onChange={(e) => setFormatStyle(e.target.value)}
                    className="w-full bg-white border border-gray-300 px-3 py-2 text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
                  >
                    <option value="ieee">IEEE Conference</option>
                    <option value="acm">ACM Journal</option>
                    <option value="springer">Springer LNCS</option>
                  </select>
                </div>

                {/* Modal Footer */}
                <div className="border-t border-gray-100 pt-4 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 bg-white border border-gray-300 hover:bg-gray-50 rounded-md transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-md text-sm font-medium shadow-sm transition-colors flex items-center gap-1.5"
                  >
                    {isCreating ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      'Create Project'
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
