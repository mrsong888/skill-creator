import { create } from "zustand";

interface SettingsState {
  backendUrl: string;
  setBackendUrl: (url: string) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  backendUrl: "http://localhost:8001",

  setBackendUrl: (url: string) => set({ backendUrl: url }),
}));
