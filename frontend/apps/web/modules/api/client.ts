"use client";
import { IceApiClient, Fetcher } from "@ice/api-client";
import { getProjectId } from "@/modules/context/projectIdGlobal";
import { env } from "@/lib/env";

// Inject X-Project-Id automatically from URL (?projectId=...) for all calls
const fetchWithProject: Fetcher = (input, init) => {
  try {
    if (typeof window !== "undefined") {
      const pid = getProjectId();
      if (pid) {
        const headers = new Headers(init?.headers as any);
        if (!headers.has("X-Project-Id")) headers.set("X-Project-Id", pid);
        return fetch(input as any, { ...(init || {}), headers });
      }
    }
  } catch {}
  return fetch(input as any, init);
};

export const api = new IceApiClient({
  baseUrl: env.API_URL,
  token: env.API_TOKEN,
  fetch: fetchWithProject,
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
  templates: {
    list: () => api.listTemplates(),
    addToProject: (projectId: string, body: { workflow_id: string; path_hint?: string | null }) => api.createBlueprintFromBundleForProject(projectId, { bundle_id: body.workflow_id, path_hint: body.path_hint ?? null }),
  },
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

export const workspaces = {
  list: () => api.listWorkspaces(),
  projects: (workspaceId: string) => api.listProjects(workspaceId),
  bootstrap: () => api.bootstrap(),
  create: (payload: { id: string; name: string }) => api.createWorkspace(payload),
  createProject: (payload: { id: string; workspace_id: string; name: string }) => api.createProject(payload),
};

export const projects = {
  blueprints: (projectId: string) => api.listProjectBlueprints(projectId),
  attach: (projectId: string, blueprintId: string) => (api as any).attachProjectBlueprint(projectId, { blueprint_id: blueprintId }),
  catalog: {
    get: (projectId: string) => api.getProjectCatalog(projectId),
    update: (projectId: string, payload: { enabled_tools: string[]; enabled_workflows: string[] }) => api.updateProjectCatalog(projectId, payload),
  },
  mounts: {
    list: (projectId: string) => api.listMounts(projectId),
    add: (projectId: string, payload: { id: string; label: string; uri: string; metadata?: Record<string, unknown> }) => api.addMount(projectId, payload),
  },
};

export const workflows = {
  create: (data: Record<string, unknown>) => (api as any).createBlueprint({ data }),
  get: (id: string) => (api as any).getBlueprint(id),
  put: (id: string, payload: Record<string, unknown>, versionLock: string) => (api as any).putBlueprint(id, payload, versionLock),
  patch: (id: string, payload: Record<string, unknown>, versionLock: string) => (api as any).patchBlueprint(id, payload, versionLock),
  delete: (id: string, versionLock: string) => (api as any).deleteBlueprint(id, versionLock),
};
