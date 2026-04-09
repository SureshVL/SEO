import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface BusinessProfile {
  city: string;
  cityCode: string;
  businessType: string;
  businessTypeLabel: string;
  keywords: string[];
  websiteUrl: string;
  projectId: string;
  projectName: string;
}

interface AppState {
  user: any | null;
  org: any | null;
  currentProject: any | null;
  apiKey: string;
  businessProfile: BusinessProfile | null;
  ga4Connected: boolean;
  gscConnected: boolean;
  ga4PropertyId: string;
  gscSiteUrl: string;

  setUser: (user: any) => void;
  setOrg: (org: any) => void;
  setCurrentProject: (project: any) => void;
  setApiKey: (key: string) => void;
  setBusinessProfile: (profile: BusinessProfile) => void;
  setGa4Connected: (connected: boolean, propertyId?: string) => void;
  setGscConnected: (connected: boolean, siteUrl?: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      org: null,
      currentProject: null,
      apiKey: process.env.NEXT_PUBLIC_API_KEY || "dev-orchestrator-key",
      businessProfile: null,
      ga4Connected: false,
      gscConnected: false,
      ga4PropertyId: "",
      gscSiteUrl: "",

      setUser: (user) => set({ user }),
      setOrg: (org) => set({ org }),
      setCurrentProject: (project) => set({ currentProject: project }),
      setApiKey: (apiKey) => set({ apiKey }),
      setBusinessProfile: (profile) => set({ businessProfile: profile }),
      setGa4Connected: (connected, propertyId) =>
        set({ ga4Connected: connected, ga4PropertyId: propertyId || "" }),
      setGscConnected: (connected, siteUrl) =>
        set({ gscConnected: connected, gscSiteUrl: siteUrl || "" }),
    }),
    {
      name: "omnirank-store",
      partialize: (state) => ({
        apiKey: state.apiKey,
        businessProfile: state.businessProfile,
        ga4Connected: state.ga4Connected,
        gscConnected: state.gscConnected,
        ga4PropertyId: state.ga4PropertyId,
        gscSiteUrl: state.gscSiteUrl,
      }),
    }
  )
);
