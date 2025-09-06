"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

type StudioUiState = {
  collapsed: Record<string, boolean>;
  toggle: (id: string) => void;
  setCollapsed: (id: string, v: boolean) => void;
};

export const useStudioUiStore = create<StudioUiState>()(persist((set, get) => ({
  collapsed: {},
  toggle: (id: string) => {
    const cur = get().collapsed[id] ?? false;
    set({ collapsed: { ...get().collapsed, [id]: !cur } });
  },
  setCollapsed: (id: string, v: boolean) => set({ collapsed: { ...get().collapsed, [id]: v } }),
}), { name: "studio-ui" }));
