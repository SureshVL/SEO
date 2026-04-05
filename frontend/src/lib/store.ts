import { create } from "zustand";

interface AppState {
  user: any | null;
  org: any | null;
  currentProject: any | null;
  apiKey: string;
  setUser: (user: any) => void;
  setOrg: (org: any) => void;
  setCurrentProject: (project: any) => void;
  setApiKey: (key: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  org: null,
  currentProject: null,
  apiKey: process.env.NEXT_PUBLIC_API_KEY || "dev-orchestrator-key",
  setUser: (user) => set({ user }),
  setOrg: (org) => set({ org }),
  setCurrentProject: (project) => set({ currentProject: project }),
  setApiKey: (apiKey) => set({ apiKey }),
}));
