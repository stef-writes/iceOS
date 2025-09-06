"use client";
import { create } from "zustand";
import type { CanvasBlueprint } from "@/modules/canvas/utils/blueprint";
import { computeSimpleDagLayout } from "@/modules/canvas/utils/autolayout";

type Selected = { id: string; type: string } | null;

type CanvasState = {
  blueprint: CanvasBlueprint | null;
  selected: Selected;
  positions: Record<string, { x: number; y: number }>;
  // History (undo/redo) captures blueprint + positions on structural changes
  _historyPast: Array<{ blueprint: CanvasBlueprint | null; positions: Record<string, { x: number; y: number }> }>;
  _historyFuture: Array<{ blueprint: CanvasBlueprint | null; positions: Record<string, { x: number; y: number }> }>;
  setBlueprint: (bp: CanvasBlueprint | null) => void;
  setSelected: (s: Selected) => void;
  setPositions: (pos: Record<string, { x: number; y: number }>) => void;
  updatePositions: (partial: Record<string, { x: number; y: number }>) => void;
  connectEdge: (source: string, target: string, targetHandle?: string) => void;
  removeEdgesByIds: (ids: string[]) => void;
  alignLeft: () => void;
  alignTop: () => void;
  distributeHorizontally: () => void;
  distributeVertically: () => void;
  autoLayout: () => void;
  undo: () => void;
  redo: () => void;
};

export const useCanvasStore = create<CanvasState>((set, get) => ({
  blueprint: null,
  selected: null,
  positions: {},
  _historyPast: [],
  _historyFuture: [],
  setBlueprint: (bp) => set((s) => ({
    _historyPast: [...s._historyPast, { blueprint: s.blueprint, positions: s.positions }],
    _historyFuture: [],
    blueprint: bp,
  })),
  setSelected: (s) => set({ selected: s }),
  setPositions: (pos) => set({ positions: pos }),
  updatePositions: (partial) => set((s) => ({ positions: { ...s.positions, ...partial } })),
  connectEdge: (source, target, targetHandle = "in") => {
    const prev = get().blueprint;
    if (!prev) return;
    const next = { ...prev, nodes: [...(prev.nodes || [])] } as any;
    const idx = next.nodes.findIndex((n: any) => n.id === target);
    if (idx >= 0) {
      const node = { ...next.nodes[idx] };
      const deps: string[] = Array.isArray(node.dependencies) ? [...node.dependencies] : [];
      if (!deps.includes(source)) deps.push(source);
      node.dependencies = deps;
      const inputs = { ...(node.inputs || {}) } as Record<string, any>;
      const current = inputs[targetHandle];
      if (Array.isArray(current)) {
        if (!current.includes(source)) inputs[targetHandle] = [...current, source];
      } else if (current && current !== source) {
        inputs[targetHandle] = source;
      } else {
        inputs[targetHandle] = source;
      }
      node.inputs = inputs;
      next.nodes[idx] = node;
      set({ blueprint: next });
    }
  },
  removeEdgesByIds: (ids) => {
    const prev = get().blueprint;
    if (!prev || ids.length === 0) return;
    const next = { ...prev, nodes: [...(prev.nodes || [])] } as any;
    ids.forEach((edgeId) => {
      const [src, tgt] = String(edgeId || "").split("->");
      const idx = next.nodes.findIndex((n: any) => n.id === tgt);
      if (idx >= 0) {
        const node = { ...next.nodes[idx] };
        node.dependencies = (node.dependencies || []).filter((d: string) => d !== src);
        if (node.inputs) {
          for (const k of Object.keys(node.inputs)) {
            const v = node.inputs[k];
            if (Array.isArray(v)) node.inputs[k] = v.filter((x: string) => x !== src);
            else if (v === src) delete node.inputs[k];
          }
        }
        next.nodes[idx] = node;
      }
    });
    set({ blueprint: next });
  },
  alignLeft: () => {
    const bp = get().blueprint;
    if (!bp) return;
    const ids = (bp.nodes || []).map((n: any) => n.id);
    if (ids.length === 0) return;
    const pos = { ...get().positions };
    const xs = ids.map((id) => (pos[id]?.x ?? 80));
    const minX = Math.min(...xs);
    const result: Record<string, { x: number; y: number }> = {};
    ids.forEach((id) => { const p = pos[id] || { x: 80, y: 60 }; result[id] = { x: minX, y: p.y }; });
    set({ positions: { ...pos, ...result } });
  },
  alignTop: () => {
    const bp = get().blueprint;
    if (!bp) return;
    const ids = (bp.nodes || []).map((n: any) => n.id);
    if (ids.length === 0) return;
    const pos = { ...get().positions };
    const ys = ids.map((id) => (pos[id]?.y ?? 60));
    const minY = Math.min(...ys);
    const result: Record<string, { x: number; y: number }> = {};
    ids.forEach((id) => { const p = pos[id] || { x: 80, y: 60 }; result[id] = { x: p.x, y: minY }; });
    set({ positions: { ...pos, ...result } });
  },
  distributeHorizontally: () => {
    const bp = get().blueprint;
    if (!bp) return;
    const ids = (bp.nodes || []).map((n: any) => n.id);
    if (ids.length <= 2) return; // nothing to distribute
    const pos = { ...get().positions };
    const sorted = [...ids].sort((a, b) => (pos[a]?.x ?? 80) - (pos[b]?.x ?? 80));
    const left = pos[sorted[0]]?.x ?? 80;
    const right = pos[sorted[sorted.length - 1]]?.x ?? (80 + 220 * (sorted.length - 1));
    const gap = (right - left) / (sorted.length - 1);
    const result: Record<string, { x: number; y: number }> = {};
    sorted.forEach((id, idx) => {
      const p = pos[id] || { x: 80, y: 60 };
      result[id] = { x: Math.round(left + idx * gap), y: p.y };
    });
    set({ positions: { ...pos, ...result } });
  },
  distributeVertically: () => {
    const bp = get().blueprint;
    if (!bp) return;
    const ids = (bp.nodes || []).map((n: any) => n.id);
    if (ids.length <= 2) return;
    const pos = { ...get().positions };
    const sorted = [...ids].sort((a, b) => (pos[a]?.y ?? 60) - (pos[b]?.y ?? 60));
    const top = pos[sorted[0]]?.y ?? 60;
    const bottom = pos[sorted[sorted.length - 1]]?.y ?? (60 + 120 * (sorted.length - 1));
    const gap = (bottom - top) / (sorted.length - 1);
    const result: Record<string, { x: number; y: number }> = {};
    sorted.forEach((id, idx) => {
      const p = pos[id] || { x: 80, y: 60 };
      result[id] = { x: p.x, y: Math.round(top + idx * gap) };
    });
    set({ positions: { ...pos, ...result } });
  },
  autoLayout: () => {
    const bp = get().blueprint as any;
    const layout = computeSimpleDagLayout(bp);
    set({ positions: { ...layout } });
  },
  undo: () => {
    const past = get()._historyPast;
    if (!past.length) return;
    const current = { blueprint: get().blueprint, positions: get().positions };
    const prev = past[past.length - 1];
    set({
      _historyPast: past.slice(0, -1),
      _historyFuture: [current, ...get()._historyFuture],
      blueprint: prev.blueprint,
      positions: prev.positions,
      selected: null,
    });
  },
  redo: () => {
    const future = get()._historyFuture;
    if (!future.length) return;
    const current = { blueprint: get().blueprint, positions: get().positions };
    const next = future[0];
    set({
      _historyPast: [...get()._historyPast, current],
      _historyFuture: future.slice(1),
      blueprint: next.blueprint,
      positions: next.positions,
      selected: null,
    });
  },
}));
