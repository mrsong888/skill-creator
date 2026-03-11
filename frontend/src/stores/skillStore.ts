import { create } from "zustand";
import {
  type SkillDetail,
  type SkillSummary,
  deleteSkill,
  getSkill,
  listSkills,
  updateSkillEnabled,
} from "@/services/api";

interface SkillState {
  skills: SkillSummary[];
  selectedSkill: SkillDetail | null;
  loading: boolean;

  loadSkills: () => Promise<void>;
  selectSkill: (name: string) => Promise<void>;
  clearSelection: () => void;
  toggleEnabled: (name: string, enabled: boolean) => Promise<void>;
  removeSkill: (name: string) => Promise<void>;
}

export const useSkillStore = create<SkillState>((set, get) => ({
  skills: [],
  selectedSkill: null,
  loading: false,

  loadSkills: async () => {
    set({ loading: true });
    const skills = await listSkills();
    set({ skills, loading: false });
  },

  selectSkill: async (name: string) => {
    const detail = await getSkill(name);
    set({ selectedSkill: detail });
  },

  clearSelection: () => set({ selectedSkill: null }),

  toggleEnabled: async (name: string, enabled: boolean) => {
    await updateSkillEnabled(name, enabled);
    set((state) => ({
      skills: state.skills.map((s) => (s.name === name ? { ...s, enabled } : s)),
    }));
  },

  removeSkill: async (name: string) => {
    await deleteSkill(name);
    await get().loadSkills();
    set({ selectedSkill: null });
  },
}));
