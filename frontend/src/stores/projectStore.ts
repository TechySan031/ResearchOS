import { create } from 'zustand';
import { api } from '../lib/api';
import { Project } from '../types';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<Project>;
  createProject: (payload: { title: string; description?: string; topic?: string; settings?: Record<string, any> }) => Promise<Project>;
  updateProject: (id: string, payload: Partial<Project>) => Promise<Project>;
  deleteProject: (id: string) => Promise<void>;
  setCurrentProject: (project: Project | null) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  isLoading: false,
  error: null,

  fetchProjects: async () => {
    set({ isLoading: true, error: null });
    try {
      // Backend now scopes to the authenticated user via JWT
      const data = await api.get<any>(`/api/v1/projects`);
      const items = Array.isArray(data) ? data : data.items || [];
      set({ projects: items, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch projects', isLoading: false });
    }
  },

  fetchProject: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const project = await api.get<Project>(`/api/v1/projects/${id}`);
      set({ currentProject: project, isLoading: false });
      return project;
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch project', isLoading: false });
      throw err;
    }
  },

  createProject: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const project = await api.post<Project>(
        `/api/v1/projects`,
        payload
      );
      set((state) => ({
        projects: [project, ...state.projects],
        currentProject: project,
        isLoading: false,
      }));
      return project;
    } catch (err: any) {
      set({ error: err.message || 'Failed to create project', isLoading: false });
      throw err;
    }
  },

  updateProject: async (id, payload) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await api.patch<Project>(`/api/v1/projects/${id}`, payload);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === id ? updated : p)),
        currentProject: state.currentProject?.id === id ? updated : state.currentProject,
        isLoading: false,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message || 'Failed to update project', isLoading: false });
      throw err;
    }
  },

  deleteProject: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await api.delete(`/api/v1/projects/${id}`);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProject: state.currentProject?.id === id ? null : state.currentProject,
        isLoading: false,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete project', isLoading: false });
      throw err;
    }
  },

  setCurrentProject: (project) => {
    set({ currentProject: project });
  },
}));
