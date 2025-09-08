"use client";
import { create } from "zustand";

export type CopilotAction = {
  id: string;
  kind: "add_node" | "edit_node" | "link" | "run" | "validate";
  target?: string | null;
  fields_changed?: string[];
  patches?: any[];
  confidence?: number;
  rationale_summary?: string | null;
};

export type CopilotMessage = {
  id: string;
  role: "user" | "assistant";
  text?: string;
  actions?: CopilotAction[];
  costs?: { estimate_usd?: number; tokens_in?: number; tokens_out?: number };
  risks?: Record<string, unknown>;
  created_at: number;
};

type State = {
  open: boolean;
  widthPct: number; // 0-100
  loading: boolean;
  provider?: string | null;
  model?: string | null;
  temperature?: number | null;
  includeSelection: boolean;
  includeCanvas: boolean;
  messages: CopilotMessage[];
  setOpen(v: boolean): void;
  setWidth(p: number): void;
  setLoading(v: boolean): void;
  setModelControls(p?: string | null, m?: string | null, t?: number | null): void;
  setContextToggles(sel: boolean, canvas: boolean): void;
  pushMessage(msg: CopilotMessage): void;
  replaceLastAssistant(msg: Partial<CopilotMessage>): void;
  clear(): void;
};

export const useCopilotStore = create<State>((set, get) => ({
  open: false,
  widthPct: 34,
  loading: false,
  provider: null,
  model: null,
  temperature: null,
  includeSelection: true,
  includeCanvas: true,
  messages: [],
  setOpen(v) { set({ open: v }); },
  setWidth(p) { const pct = Math.min(60, Math.max(20, Math.floor(p))); set({ widthPct: pct }); },
  setLoading(v) { set({ loading: v }); },
  setModelControls(p, m, t) { set({ provider: p ?? null, model: m ?? null, temperature: t ?? null }); },
  setContextToggles(sel, canvas) { set({ includeSelection: sel, includeCanvas: canvas }); },
  pushMessage(msg) { set({ messages: [...get().messages, msg] }); },
  replaceLastAssistant(msg) {
    const arr = get().messages.slice();
    for (let i = arr.length - 1; i >= 0; i -= 1) {
      if (arr[i].role === "assistant") {
        arr[i] = { ...arr[i], ...msg } as CopilotMessage;
        break;
      }
    }
    set({ messages: arr });
  },
  clear() { set({ messages: [] }); },
}));
