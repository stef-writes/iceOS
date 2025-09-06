"use client";
import { create } from "zustand";

export type ExecEvent = { event: string; payload: any };

type ExecutionState = {
  runId: string | null;
  events: ExecEvent[];
  nodeStatus: Record<string, "queued" | "running" | "completed" | "failed">;
  finished: boolean;
  success: boolean | null;
  start: (eventsUrl: string) => void;
  stop: () => void;
};

export const useExecutionStore = create<ExecutionState>((set) => {
  let es: EventSource | null = null;
  return {
    runId: null,
    events: [],
    nodeStatus: {},
    finished: false,
    success: null,
    start: (eventsUrl: string) => {
      try { es?.close(); } catch {}
      es = new EventSource(eventsUrl);
      set({ runId: eventsUrl, events: [], nodeStatus: {}, finished: false, success: null });
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          // Default channel when server doesn't emit named events
          set((s) => ({ events: [...s.events, { event: "message", payload: data }] }));
        } catch {
          set((s) => ({ events: [...s.events, { event: "message", payload: e.data }] }));
        }
      };
      es.addEventListener("node.started", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent).data);
          const nodeId = String(payload.node_id ?? payload.id ?? "");
          if (!nodeId) return;
          set((s) => ({
            events: [...s.events, { event: "node.started", payload }],
            nodeStatus: { ...s.nodeStatus, [nodeId]: "running" },
          }));
        } catch {}
      });
      es.addEventListener("node.completed", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent).data);
          const nodeId = String(payload.node_id ?? payload.id ?? "");
          if (!nodeId) return;
          set((s) => ({
            events: [...s.events, { event: "node.completed", payload }],
            nodeStatus: { ...s.nodeStatus, [nodeId]: "completed" },
          }));
        } catch {}
      });
      es.addEventListener("node.failed", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent).data);
          const nodeId = String(payload.node_id ?? payload.id ?? "");
          if (!nodeId) return;
          set((s) => ({
            events: [...s.events, { event: "node.failed", payload }],
            nodeStatus: { ...s.nodeStatus, [nodeId]: "failed" },
          }));
        } catch {}
      });
      es.addEventListener("workflow.finished", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent).data);
          const ok = !!payload.success;
          set((s) => ({ events: [...s.events, { event: "workflow.finished", payload }], finished: true, success: ok }));
        } catch {
          set((s) => ({ events: [...s.events, { event: "workflow.finished", payload: {} }], finished: true, success: null }));
        }
      });
      es.onerror = () => {
        set((s) => ({ events: [...s.events, { event: "error", payload: "SSE connection lost" }] }));
        try { es?.close(); } catch {}
        es = null;
      };
    },
    stop: () => {
      try { es?.close(); } catch {}
      es = null;
      set({ runId: null });
    },
  };
});
