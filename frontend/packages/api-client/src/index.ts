export type Fetcher = (input: RequestInfo, init?: RequestInit) => Promise<Response>;

export interface ClientOptions {
  baseUrl: string;
  token?: string;
  fetch?: Fetcher;
}

export class IceApiClient {
  private readonly baseUrl: string;
  private readonly token?: string;
  private readonly _fetch: Fetcher;

  constructor(opts: ClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.token = opts.token;
    const f = opts.fetch ?? fetch;
    // Bind fetch to globalThis to avoid Illegal invocation errors in some runtimes
    this._fetch = (input: RequestInfo, init?: RequestInit) => f.call(globalThis, input as any, init);
  }

  private headers(extra?: Record<string, string>): HeadersInit {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.token) h["Authorization"] = `Bearer ${this.token}`;
    return { ...h, ...(extra || {}) };
  }

  private async _json<T>(res: Response): Promise<T> {
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) return res.json() as Promise<T>;
    const text = await res.text();
    return JSON.parse(text) as T;
  }

  // --------------------------- Builder (MCP) ---------------------------
  async suggest(body: { text: string; canvas_state?: Record<string, unknown>; provider?: string | null; model?: string | null; temperature?: number | null; }): Promise<{ patches: any[]; questions?: string[]; missing_fields?: Record<string, unknown>; cost_estimate_usd?: number; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/suggest`, { method: "POST", headers: this.headers(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`suggest failed: ${r.status}`);
    return this._json(r);
  }

  async propose(body: { text: string; base?: Record<string, unknown> | null; }): Promise<{ blueprint: Record<string, unknown>; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/propose`, { method: "POST", headers: this.headers(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`propose failed: ${r.status}`);
    return this._json(r);
  }

  async apply(body: { blueprint: Record<string, unknown>; patches: Array<Record<string, unknown>>; }): Promise<{ blueprint: Record<string, unknown>; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/apply`, { method: "POST", headers: this.headers(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`apply failed: ${r.status}`);
    return this._json(r);
  }

  // --------------------------- Drafts (If-Match) -----------------------
  async getDraft(key: string): Promise<{ data: Record<string, unknown>; version: number; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/drafts/${encodeURIComponent(key)}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`draft get failed: ${r.status}`);
    return this._json(r);
  }

  async putDraft(key: string, payload: { data: Record<string, unknown>; version?: number }, ifMatch?: number): Promise<{ key: string; ok: boolean; version: number; }> {
    const headers = this.headers(ifMatch != null ? { "If-Match": String(ifMatch) } : undefined);
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/drafts/${encodeURIComponent(key)}`, { method: "PUT", headers, body: JSON.stringify({ version: payload.version ?? 0, data: payload.data }) });
    if (!r.ok) throw new Error(`draft put failed: ${r.status}`);
    return this._json(r);
  }

  async deleteDraft(key: string): Promise<{ key: string; ok: boolean; version: number; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/drafts/${encodeURIComponent(key)}`, { method: "DELETE", headers: this.headers() });
    if (!r.ok) throw new Error(`draft delete failed: ${r.status}`);
    return this._json(r);
  }

  // --------------------------- Preview sandbox -------------------------
  async previewTool(body: { language?: string; code: string; inputs?: Record<string, unknown>; imports?: string[]; timeout_seconds?: number; }): Promise<{ success: boolean; output?: unknown; error?: string; logs?: Array<Record<string, unknown>>; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/preview/tool`, { method: "POST", headers: this.headers(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`previewTool failed: ${r.status}`);
    return this._json(r);
  }

  // --------------------------- Sessions --------------------------------
  async getSession(sessionId: string): Promise<{ data: Record<string, unknown> }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/sessions/${encodeURIComponent(sessionId)}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`session get failed: ${r.status}`);
    return this._json(r);
  }

  async putSession(sessionId: string, payload: { data: Record<string, unknown> }): Promise<{ session_id: string; ok: boolean; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/sessions/${encodeURIComponent(sessionId)}`, { method: "PUT", headers: this.headers(), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`session put failed: ${r.status}`);
    return this._json(r);
  }

  async deleteSession(sessionId: string): Promise<{ session_id: string; ok: boolean; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/builder/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE", headers: this.headers() });
    if (!r.ok) throw new Error(`session delete failed: ${r.status}`);
    return this._json(r);
  }

  // --------------------------- Library ---------------------------------
  async listLibrary(params: { q?: string; kind?: "component" | "blueprint"; limit?: number }): Promise<{ items: Array<Record<string, unknown>>; }> {
    const q = new URLSearchParams();
    if (params.q) q.set("q", params.q);
    if (params.kind) q.set("kind", params.kind);
    if (params.limit != null) q.set("limit", String(params.limit));
    const r = await this._fetch(`${this.baseUrl}/api/v1/library/assets/index?${q.toString()}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`library index failed: ${r.status}`);
    return this._json(r);
  }

  async addAsset(payload: { label: string; content: string; mime?: string; scope?: string; org_id?: string; user_id?: string; }): Promise<Record<string, unknown>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/library/assets`, { method: "POST", headers: this.headers(), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`library add asset failed: ${r.status}`);
    return this._json(r);
  }

  async listAssets(params: { org_id?: string; user_id?: string; prefix?: string; limit?: number; }): Promise<{ items: Array<Record<string, unknown>>; }> {
    const q = new URLSearchParams();
    if (params.org_id) q.set("org_id", params.org_id);
    if (params.user_id) q.set("user_id", params.user_id);
    if (params.prefix) q.set("prefix", params.prefix);
    if (params.limit != null) q.set("limit", String(params.limit));
    const r = await this._fetch(`${this.baseUrl}/api/v1/library/assets?${q.toString()}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`library list assets failed: ${r.status}`);
    return this._json(r);
  }

  async getAsset(label: string, params: { org_id?: string; user_id?: string; } = {}): Promise<Record<string, unknown>> {
    const q = new URLSearchParams();
    if (params.org_id) q.set("org_id", params.org_id);
    if (params.user_id) q.set("user_id", params.user_id);
    const r = await this._fetch(`${this.baseUrl}/api/v1/library/assets/${encodeURIComponent(label)}?${q.toString()}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`library get asset failed: ${r.status}`);
    return this._json(r);
  }

  async deleteAsset(label: string, params: { org_id?: string; user_id?: string; } = {}): Promise<{ ok: boolean; key: string; }> {
    const q = new URLSearchParams();
    if (params.org_id) q.set("org_id", params.org_id);
    if (params.user_id) q.set("user_id", params.user_id);
    const r = await this._fetch(`${this.baseUrl}/api/v1/library/assets/${encodeURIComponent(label)}?${q.toString()}`, { method: "DELETE", headers: this.headers() });
    if (!r.ok) throw new Error(`library delete asset failed: ${r.status}`);
    return this._json(r);
  }

  // --------------------------- MCP Repo (components/blueprints) -----------
  async listMcpComponents(): Promise<{ stored: Array<Record<string, unknown>>; registered: Array<Record<string, unknown>>; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/components`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`mcp list components failed: ${r.status}`);
    return this._json(r);
  }

  async getMcpComponent(componentType: string, name: string): Promise<{ data: Record<string, unknown>; versionLock?: string; } & Record<string, unknown>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/components/${encodeURIComponent(componentType)}/${encodeURIComponent(name)}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`mcp get component failed: ${r.status}`);
    // Expose lock via header if present
    const obj = await this._json<Record<string, unknown>>(r);
    const versionLock = r.headers.get("X-Version-Lock") ?? undefined;
    return { ...obj, versionLock } as any;
  }

  async updateMcpComponent(componentType: string, name: string, definition: Record<string, unknown>, versionLock: string): Promise<{ name: string; type: string; version_lock: string; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/components/${encodeURIComponent(componentType)}/${encodeURIComponent(name)}`, { method: "PUT", headers: this.headers({ "X-Version-Lock": versionLock }), body: JSON.stringify(definition) });
    if (!r.ok) throw new Error(`mcp update component failed: ${r.status}`);
    return this._json(r);
  }

  async registerMcpComponent(definition: Record<string, unknown>): Promise<Record<string, unknown>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/components/register`, { method: "POST", headers: this.headers(), body: JSON.stringify(definition) });
    if (!r.ok) throw new Error(`mcp register component failed: ${r.status}`);
    return this._json(r);
  }

  async validateMcpComponent(definition: Record<string, unknown>): Promise<Record<string, unknown>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/components/validate`, { method: "POST", headers: this.headers(), body: JSON.stringify(definition) });
    if (!r.ok) throw new Error(`mcp validate component failed: ${r.status}`);
    return this._json(r);
  }

  async deleteMcpComponent(componentType: string, name: string): Promise<void> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/components/${encodeURIComponent(componentType)}/${encodeURIComponent(name)}`, { method: "DELETE", headers: this.headers() });
    if (!r.ok && r.status !== 204) throw new Error(`mcp delete component failed: ${r.status}`);
  }

  // --------------------------- MCP Partial Blueprints ----------------------
  async createPartialBlueprint(initialNode?: Record<string, unknown> | null): Promise<Record<string, unknown>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/blueprints/partial`, { method: "POST", headers: this.headers(), body: initialNode ? JSON.stringify(initialNode) : null });
    if (!r.ok) throw new Error(`mcp create partial failed: ${r.status}`);
    return this._json(r);
  }

  async getPartialBlueprint(blueprintId: string): Promise<{ data: Record<string, unknown>; versionLock?: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/blueprints/partial/${encodeURIComponent(blueprintId)}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`mcp get partial failed: ${r.status}`);
    const obj = await this._json<Record<string, unknown>>(r);
    const versionLock = r.headers.get("X-Version-Lock") ?? undefined;
    return { data: obj, versionLock };
  }

  async updatePartialBlueprint(blueprintId: string, update: Record<string, unknown>, versionLock: string): Promise<Record<string, unknown>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/blueprints/partial/${encodeURIComponent(blueprintId)}`, { method: "PUT", headers: this.headers({ "X-Version-Lock": versionLock }), body: JSON.stringify(update) });
    if (!r.ok) throw new Error(`mcp update partial failed: ${r.status}`);
    return this._json(r);
  }

  async finalizePartialBlueprint(blueprintId: string, versionLock: string): Promise<Record<string, unknown>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/blueprints/partial/${encodeURIComponent(blueprintId)}/finalize`, { method: "POST", headers: this.headers({ "X-Version-Lock": versionLock }) });
    if (!r.ok) throw new Error(`mcp finalize partial failed: ${r.status}`);
    return this._json(r);
  }

  async suggestPartialBlueprint(blueprintId: string, body?: { top_k?: number; allowed_types?: string[]; commit?: boolean; versionLock?: string }): Promise<Record<string, unknown>> {
    const headers = body?.commit && body?.versionLock ? this.headers({ "X-Version-Lock": body.versionLock }) : this.headers();
    const payload: Record<string, unknown> = {
      top_k: body?.top_k ?? 5,
      allowed_types: body?.allowed_types,
      commit: !!body?.commit,
    };
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/blueprints/partial/${encodeURIComponent(blueprintId)}/suggest`, { method: "POST", headers, body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`mcp suggest partial failed: ${r.status}`);
    return this._json(r);
  }

  async getMcpBlueprint(blueprintId: string): Promise<Record<string, unknown>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/blueprints/${encodeURIComponent(blueprintId)}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`mcp get blueprint failed: ${r.status}`);
    return this._json(r);
  }

  // --------------------------- MCP Runs (SSE) ------------------------------
  async startMcpRun(payload: { blueprint_id?: string; blueprint?: Record<string, unknown>; options?: { max_parallel?: number } }): Promise<{ run_id: string; status_endpoint: string; events_endpoint: string; }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/mcp/runs`, { method: "POST", headers: this.headers(), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`mcp start run failed: ${r.status}`);
    return this._json(r);
  }

  mcpEventsUrl(runId: string): string {
    return `${this.baseUrl}/api/v1/mcp/runs/${encodeURIComponent(runId)}/events`;
  }

  // --------------------------- Executions API ------------------------------
  async listExecutions(limit?: number): Promise<{ executions: Array<{ execution_id: string; status: string; blueprint_id: string }> }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/executions/`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`executions list failed: ${r.status}`);
    const data = await this._json<{ executions: Array<{ execution_id: string; status: string; blueprint_id: string }> }>(r);
    if (typeof limit === "number" && limit > 0) {
      return { executions: data.executions.slice(0, limit) };
    }
    return data;
  }

  async getExecutionStatus(executionId: string): Promise<{ execution_id: string; status: string; blueprint_id?: string; result?: Record<string, unknown>; error?: string; events?: Array<{ event: string; payload: unknown }> }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/executions/${encodeURIComponent(executionId)}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`execution status failed: ${r.status}`);
    return this._json(r);
  }

  async startExecution(payload: { blueprint_id: string; inputs?: Record<string, unknown> | null; wait_seconds?: number | null }): Promise<{ execution_id: string; status: string; result?: Record<string, unknown> | null }> {
    const search = new URLSearchParams();
    if (payload.wait_seconds != null) search.set("wait_seconds", String(payload.wait_seconds));
    const r = await this._fetch(`${this.baseUrl}/api/v1/executions/?${search.toString()}`, { method: "POST", headers: this.headers(), body: JSON.stringify({ blueprint_id: payload.blueprint_id, inputs: payload.inputs ?? null }) });
    if (!r.ok) throw new Error(`execution start failed: ${r.status}`);
    return this._json(r);
  }

  // --------------------------- Templates -----------------------------------
  async listTemplates(): Promise<{ templates: Array<{ id: string; bundle: string; path: string; description?: string }> }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/templates/`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`templates list failed: ${r.status}`);
    return this._json(r);
  }

  async createBlueprintFromWorkflowForProject(projectId: string, body: { workflow_id: string; path_hint?: string | null }): Promise<{ id: string; version_lock: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/blueprints/from-workflow`, { method: "POST", headers: this.headers(), body: JSON.stringify({ workflow_id: body.workflow_id, path_hint: body.path_hint ?? null }) });
    if (!r.ok) throw new Error(`from-workflow failed: ${r.status}`);
    return this._json(r);
  }

  // Back-compat alias (calls /from-workflow under the hood)
  async createBlueprintFromBundleForProject(projectId: string, body: { bundle_id: string; path_hint?: string | null }): Promise<{ id: string; version_lock: string }> {
    return this.createBlueprintFromWorkflowForProject(projectId, { workflow_id: body.bundle_id, path_hint: body.path_hint ?? null });
  }

  // --------------------------- Workspaces/Projects --------------------------
  // --------------------------- Workflows (Blueprints) -----------------------
  async createBlueprint(payload: { data: Record<string, unknown> }): Promise<{ id: string; version_lock: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/blueprints/`, { method: "POST", headers: this.headers({ "X-Version-Lock": "__new__" }), body: JSON.stringify(payload.data) });
    if (!r.ok) throw new Error(`blueprint create failed: ${r.status}`);
    return this._json(r);
  }

  async getBlueprint(blueprintId: string): Promise<{ data: Record<string, unknown>; version_lock: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/blueprints/${encodeURIComponent(blueprintId)}`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`blueprint get failed: ${r.status}`);
    return this._json(r);
  }

  async patchBlueprint(blueprintId: string, payload: Record<string, unknown>, versionLock: string): Promise<{ id: string; node_count: number }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/blueprints/${encodeURIComponent(blueprintId)}`, { method: "PATCH", headers: this.headers({ "X-Version-Lock": versionLock }), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`blueprint patch failed: ${r.status}`);
    return this._json(r);
  }

  async putBlueprint(blueprintId: string, payload: Record<string, unknown>, versionLock: string): Promise<{ id: string; version_lock: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/blueprints/${encodeURIComponent(blueprintId)}`, { method: "PUT", headers: this.headers({ "X-Version-Lock": versionLock }), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`blueprint put failed: ${r.status}`);
    return this._json(r);
  }

  async deleteBlueprint(blueprintId: string, versionLock: string): Promise<void> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/blueprints/${encodeURIComponent(blueprintId)}`, { method: "DELETE", headers: this.headers({ "X-Version-Lock": versionLock }) });
    if (!r.ok) throw new Error(`blueprint delete failed: ${r.status}`);
  }
  async listWorkspaces(): Promise<Array<{ id: string; name: string }>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/workspaces`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`workspaces list failed: ${r.status}`);
    return this._json(r);
  }

  async listProjects(workspaceId: string): Promise<Array<{ id: string; workspace_id: string; name: string }>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/workspaces/${encodeURIComponent(workspaceId)}/projects`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`projects list failed: ${r.status}`);
    return this._json(r);
  }

  async createWorkspace(payload: { id: string; name: string }): Promise<{ id: string; name: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/workspaces`, { method: "POST", headers: this.headers(), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`workspace create failed: ${r.status}`);
    return this._json(r);
  }

  async createProject(payload: { id: string; workspace_id: string; name: string }): Promise<{ id: string; workspace_id: string; name: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects`, { method: "POST", headers: this.headers(), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`project create failed: ${r.status}`);
    return this._json(r);
  }

  async bootstrap(): Promise<{ workspace_id: string; project_id: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/bootstrap`, { method: "POST", headers: this.headers() });
    if (!r.ok) throw new Error(`bootstrap failed: ${r.status}`);
    return this._json(r);
  }

  // --------------------------- Projects: Blueprints/Catalog/Mounts -----------
  async listProjectBlueprints(projectId: string): Promise<{ blueprint_ids: string[] }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/blueprints`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`project blueprints failed: ${r.status}`);
    return this._json(r);
  }

  async attachProjectBlueprint(projectId: string, payload: { blueprint_id: string }): Promise<{ id: string; version_lock: string }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/blueprints/attach`, { method: "POST", headers: this.headers(), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`project attach blueprint failed: ${r.status}`);
    return this._json(r);
  }

  async detachProjectBlueprint(projectId: string, blueprintId: string): Promise<void> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/blueprints/${encodeURIComponent(blueprintId)}`, { method: "DELETE", headers: this.headers() });
    if (!r.ok) throw new Error(`project detach blueprint failed: ${r.status}`);
  }

  async getProjectCatalog(projectId: string): Promise<{ tools: Array<{ name: string; type: string; enabled: boolean }>; workflows: Array<{ name: string; type: string; enabled: boolean }>; agents: Array<{ name: string; type: string; enabled: boolean }> }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/catalog`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`project catalog failed: ${r.status}`);
    return this._json(r);
  }

  async updateProjectCatalog(projectId: string, payload: { enabled_tools: string[]; enabled_workflows: string[] }): Promise<{ id: string; workspace_id: string; name: string; enabled_tools: string[]; enabled_workflows: string[] }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/catalog`, { method: "PUT", headers: this.headers(), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`update catalog failed: ${r.status}`);
    return this._json(r);
  }

  async listMounts(projectId: string): Promise<Array<{ id: string; project_id: string; label: string; uri: string; metadata?: Record<string, unknown> }>> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/mounts`, { method: "GET", headers: this.headers() });
    if (!r.ok) throw new Error(`mounts list failed: ${r.status}`);
    return this._json(r);
  }

  async addMount(projectId: string, payload: { id: string; label: string; uri: string; metadata?: Record<string, unknown> }): Promise<{ id: string; project_id: string; label: string; uri: string; metadata?: Record<string, unknown> }> {
    const r = await this._fetch(`${this.baseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/mounts`, { method: "POST", headers: this.headers(), body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`mount add failed: ${r.status}`);
    return this._json(r);
  }
  // Type hints only; actual methods defined below
}

// Meta APIs (node schemas)
export interface NodeSchemaResponse {
  type: string;
  json_schema: Record<string, unknown>;
}

export class IceApiMetaClient extends IceApiClient {
  async listNodeTypes(): Promise<string[]> {
    const r = await (this as any)._fetch(`${(this as any).baseUrl}/api/v1/meta/nodes/types`, { method: "GET", headers: (this as any).headers() });
    if (!r.ok) throw new Error(`list node types failed: ${r.status}`);
    return (this as any)._json(r);
  }
  async getNodeSchema(nodeType: string): Promise<NodeSchemaResponse> {
    const r = await (this as any)._fetch(`${(this as any).baseUrl}/api/v1/meta/nodes/${encodeURIComponent(nodeType)}/schema`, { method: "GET", headers: (this as any).headers() });
    if (!r.ok) throw new Error(`get node schema failed: ${r.status}`);
    return (this as any)._json(r);
  }
}
