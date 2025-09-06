"use client";
import { IceApiClient } from "@ice/api-client";
import { env } from "@/lib/env";

export const api = new IceApiClient({
  baseUrl: env.API_URL,
  token: env.API_TOKEN,
});

export const builder = {
  suggest: (body: { text: string; canvas_state?: Record<string, unknown>; provider?: string | null; model?: string | null; temperature?: number | null; }) =>
    api.suggest({ canvas_state: {}, ...body }),
  propose: (body: { text: string; base?: Record<string, unknown> | null }) =>
    api.propose(body),
  apply: (body: { blueprint: Record<string, unknown>; patches: Array<Record<string, unknown>> }) =>
    api.apply(body),
  previewTool: (body: { language?: string; code: string; inputs?: Record<string, unknown>; imports?: string[]; timeout_seconds?: number; }) =>
    api.previewTool(body),
  drafts: {
    get: (key: string) => api.getDraft(key),
    put: (key: string, payload: { data: Record<string, unknown>; version?: number }, ifMatch?: number) =>
      api.putDraft(key, payload, ifMatch),
    delete: (key: string) => api.deleteDraft(key),
  },
};

export const library = {
  index: (p?: { q?: string; kind?: "component" | "blueprint"; limit?: number }) => api.listLibrary(p ?? {}),
  assets: {
    list: (p?: { org_id?: string; user_id?: string; prefix?: string; limit?: number }) => api.listAssets(p ?? {}),
    create: (payload: { label: string; content: string; mime?: string; scope?: string; org_id?: string; user_id?: string }) => api.addAsset(payload),
    get: (label: string, p?: { org_id?: string; user_id?: string }) => api.getAsset(label, p ?? {}),
    delete: (label: string, p?: { org_id?: string; user_id?: string }) => api.deleteAsset(label, p ?? {}),
  },
};

export const sessions = {
  get: (sessionId: string) => api.getSession(sessionId),
  put: (sessionId: string, data: Record<string, unknown>) => api.putSession(sessionId, { data }),
  delete: (sessionId: string) => api.deleteSession(sessionId),
};

export const mcp = {
  components: {
    list: () => api.listMcpComponents(),
    get: (type: string, name: string) => api.getMcpComponent(type, name),
    update: (type: string, name: string, def: Record<string, unknown>, lock: string) => api.updateMcpComponent(type, name, def, lock),
    register: (def: Record<string, unknown>) => api.registerMcpComponent(def),
    validate: (def: Record<string, unknown>) => api.validateMcpComponent(def),
    delete: (type: string, name: string) => api.deleteMcpComponent(type, name),
  },
  blueprints: {
    get: (id: string) => api.getMcpBlueprint(id),
    partial: {
      create: (initialNode?: Record<string, unknown>) => api.createPartialBlueprint(initialNode),
      get: (id: string) => api.getPartialBlueprint(id),
      update: (id: string, update: Record<string, unknown>, lock: string) => api.updatePartialBlueprint(id, update, lock),
      finalize: (id: string, lock: string) => api.finalizePartialBlueprint(id, lock),
      suggest: (id: string, opts?: { top_k?: number; allowed_types?: string[]; commit?: boolean; versionLock?: string }) => api.suggestPartialBlueprint(id, opts),
    },
  },
  runs: {
    start: (payload: { blueprint_id?: string; blueprint?: Record<string, unknown>; options?: { max_parallel?: number } }) => api.startMcpRun(payload),
    eventsUrl: (runId: string) => api.mcpEventsUrl(runId),
  },
};

export const executions = {
  list: (limit?: number) => api.listExecutions(limit),
  status: (id: string) => api.getExecutionStatus(id),
  start: (payload: { blueprint_id: string; inputs?: Record<string, unknown> | null; wait_seconds?: number | null }) => api.startExecution(payload),
};
