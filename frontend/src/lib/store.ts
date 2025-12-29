/**
 * Global state management with Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project, OutlineSection, Source } from './api';

// ============================================================================
// Auth Store
// ============================================================================

interface AuthState {
  token: string | null;
  userId: string | null;
  setAuth: (token: string, userId: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userId: null,
      setAuth: (token, userId) => set({ token, userId }),
      clearAuth: () => set({ token: null, userId: null }),
    }),
    {
      name: 'auth-storage',
    }
  )
);

// ============================================================================
// Project Store
// ============================================================================

interface ProjectState {
  currentProject: Project | null;
  projects: Project[];
  setCurrentProject: (project: Project | null) => void;
  setProjects: (projects: Project[]) => void;
  addProject: (project: Project) => void;
  updateProject: (id: string, updates: Partial<Project>) => void;
  removeProject: (id: string) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  currentProject: null,
  projects: [],
  setCurrentProject: (project) => set({ currentProject: project }),
  setProjects: (projects) => set({ projects }),
  addProject: (project) => set((state) => ({ projects: [...state.projects, project] })),
  updateProject: (id, updates) =>
    set((state) => ({
      projects: state.projects.map((p) => (p.id === id ? { ...p, ...updates } : p)),
      currentProject:
        state.currentProject?.id === id
          ? { ...state.currentProject, ...updates }
          : state.currentProject,
    })),
  removeProject: (id) =>
    set((state) => ({
      projects: state.projects.filter((p) => p.id !== id),
      currentProject: state.currentProject?.id === id ? null : state.currentProject,
    })),
}));

// ============================================================================
// Outline Store
// ============================================================================

interface OutlineState {
  sections: OutlineSection[];
  selectedSection: OutlineSection | null;
  setSections: (sections: OutlineSection[]) => void;
  setSelectedSection: (section: OutlineSection | null) => void;
  addSection: (section: OutlineSection) => void;
  updateSection: (id: string, updates: Partial<OutlineSection>) => void;
  removeSection: (id: string) => void;
}

export const useOutlineStore = create<OutlineState>((set) => ({
  sections: [],
  selectedSection: null,
  setSections: (sections) => set({ sections }),
  setSelectedSection: (section) => set({ selectedSection: section }),
  addSection: (section) => set((state) => ({ sections: [...state.sections, section] })),
  updateSection: (id, updates) =>
    set((state) => ({
      sections: state.sections.map((s) => (s.id === id ? { ...s, ...updates } : s)),
      selectedSection:
        state.selectedSection?.id === id
          ? { ...state.selectedSection, ...updates }
          : state.selectedSection,
    })),
  removeSection: (id) =>
    set((state) => ({
      sections: state.sections.filter((s) => s.id !== id),
      selectedSection: state.selectedSection?.id === id ? null : state.selectedSection,
    })),
}));

// ============================================================================
// Sources Store
// ============================================================================

interface SourcesState {
  sources: Source[];
  setSources: (sources: Source[]) => void;
  addSource: (source: Source) => void;
  updateSource: (id: string, updates: Partial<Source>) => void;
  removeSource: (id: string) => void;
}

export const useSourcesStore = create<SourcesState>((set) => ({
  sources: [],
  setSources: (sources) => set({ sources }),
  addSource: (source) => set((state) => ({ sources: [...state.sources, source] })),
  updateSource: (id, updates) =>
    set((state) => ({
      sources: state.sources.map((s) => (s.id === id ? { ...s, ...updates } : s)),
    })),
  removeSource: (id) =>
    set((state) => ({
      sources: state.sources.filter((s) => s.id !== id),
    })),
}));

// ============================================================================
// Editor Store
// ============================================================================

interface EditorState {
  content: string;
  isDirty: boolean;
  lastSaved: Date | null;
  setContent: (content: string) => void;
  markSaved: () => void;
  reset: () => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  content: '',
  isDirty: false,
  lastSaved: null,
  setContent: (content) => set({ content, isDirty: true }),
  markSaved: () => set({ isDirty: false, lastSaved: new Date() }),
  reset: () => set({ content: '', isDirty: false, lastSaved: null }),
}));

// ============================================================================
// UI Store
// ============================================================================

interface UIState {
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  rightPanelContent: 'sources' | 'chat' | 'citations' | null;
  theme: 'light' | 'dark' | 'system';
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setRightPanel: (content: 'sources' | 'chat' | 'citations' | null) => void;
  toggleRightPanel: (content: 'sources' | 'chat' | 'citations') => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      rightPanelOpen: false,
      rightPanelContent: null,
      theme: 'system',
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setRightPanel: (content) =>
        set({ rightPanelOpen: content !== null, rightPanelContent: content }),
      toggleRightPanel: (content) =>
        set((state) =>
          state.rightPanelContent === content && state.rightPanelOpen
            ? { rightPanelOpen: false, rightPanelContent: null }
            : { rightPanelOpen: true, rightPanelContent: content }
        ),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'ui-storage',
    }
  )
);

