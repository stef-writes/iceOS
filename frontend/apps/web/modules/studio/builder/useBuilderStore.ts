"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

type BuilderState = {
  text: string;
  canvasState: string; // JSON string containing { blueprint?: any }
  patches: any[];
  proposedBlueprint: any | null;
  setText: (v: string) => void;
  setCanvasState: (v: string) => void;
  setPatches: (v: any[]) => void;
  setProposedBlueprint: (bp: any | null) => void;
};

export const useBuilderStore = create<BuilderState>()(persist((set) => ({
  text: "",
  canvasState: '{\n  "blueprint": {"nodes": []}\n}',
  patches: [],
  proposedBlueprint: null,
  setText: (v) => set({ text: v }),
  setCanvasState: (v) => set({ canvasState: v }),
  setPatches: (v) => set({ patches: Array.isArray(v) ? v : [] }),
  setProposedBlueprint: (bp) => set({ proposedBlueprint: bp }),
}), { name: "builder-store" }));

export function getBaseBlueprint(canvasState: string): any | null {
  try {
    const obj = JSON.parse(canvasState || "{}");
    return obj?.blueprint ?? null;
  } catch {
    return null;
  }
}
