AI Builder integration (Studio & Canvas)

Scope: minimal backend-first integration for the co‑creator. This guide shows how Studio/Canvas can call the Builder endpoints, surface Q/A and cost, save drafts, and preview code safely.
Manual-first principle: every flow must be possible without AI; Builder endpoints are accelerators layered on top. UI must expose manual component CRUD, partial blueprint editing/finalization, and runs irrespective of AI availability.

MCP endpoints
- POST `/api/v1/builder/suggest`
  - body: `{ "text": string, "canvas_state": object, "provider?": string, "model?": string, "temperature?": number }`
  - returns: `{ patches: NodePatch[], questions?: string[], missing_fields?: object, cost_estimate_usd?: number }`
- POST `/api/v1/builder/propose`
  - body: `{ "text": string, "base?": PartialBlueprint }`
  - returns: `{ blueprint: PartialBlueprint }`
- POST `/api/v1/builder/apply`
  - body: `{ "blueprint": PartialBlueprint, "patches": NodePatch[] }`
  - returns: `{ blueprint: PartialBlueprint }`

Drafts & Sessions
- Drafts API: `PUT/GET/DELETE /api/v1/builder/drafts/{key}`
  - store in‑progress designs (JSON). TTL via `ICE_BUILDER_DRAFT_TTL_SECONDS`.
  - optimistic concurrency: include header `If-Match: <version>` to avoid clobbering
- Sessions API: `PUT/GET/DELETE /api/v1/builder/sessions/{session_id}`
  - persist plan history/preferences per session. Use `session_id` header/query param in UI state.

Preview sandbox (safe code)
- POST `/api/v1/builder/preview/tool`
  - body: `{ code: string, input?: object }`
  - returns: `{ success: boolean, output?: object, error?: string, logs?: object[] }`
  - Runs in a constrained sandbox: WASM-only (no fallback), no network/filesystem, strict CPU/mem/time, import allowlist.

SSE wiring (Execution Drawer)
- For MCP runs: subscribe to `GET /api/v1/mcp/runs/{run_id}/events` and display event stream (`workflow.*`, `node.*`).
- For the `executions` API: poll `GET /api/v1/executions/{execution_id}` for status/events (DB-backed record). UI may support both.

UI flow (suggest)
1. Build `canvas_state` with current partial blueprint and context.
2. Optional model overrides from UI: `provider`, `model`, `temperature`.
3. Call `POST /api/v1/builder/suggest`.
4. Render `questions` and `missing_fields` as a Q/A prompt.
5. Show `cost_estimate_usd` near the suggest CTA.
6. Apply `patches` to the on‑screen partial blueprint and let user accept.
7. Save the evolving design to Drafts using a deterministic `key`.

UI flow (drafts)
- Save: `PUT /api/v1/builder/drafts/{key}` with `{ payload: <your JSON> }`.
- Load: `GET /api/v1/builder/drafts/{key}`.
- Delete: `DELETE /api/v1/builder/drafts/{key}`.

Model policy & overrides
- Backend defaults read from env via `_EnvModelPolicy` and Planner defaults.
- Frontend can override per request by passing `provider`, `model`, `temperature` to `/suggest`.

Auth
- Use existing Bearer token and `X-Org-Id`/`X-User-Id` headers as in other API calls.

Minimal example (suggest)
```
curl -X POST "$API_BASE/api/v1/builder/suggest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Draft a two-node flow: llm → tool:writer",
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0,
    "canvas_state": {"blueprint": {"nodes": []}}
  }'
```

Notes
- Components live in `ice_builder` (brain). `ice_api` is transport only.
- Retrieval context (tool schemas, blueprints, runs, library) is injected automatically.

---

Studio / Canvas UX (aligned to inspiration)

- Library as Source of Truth
  - Tabs: Repo (Components, Blueprints) and Knowledge (user assets).
  - Filters: kind (components/blueprints), type (tool/agent/workflow/code/llm/swarm), search (name/tags), sort (updated/name).
  - Grid: NodeCards with actions: Open in Studio, Open on Canvas, Copy ID, View usages.
  - Drawer: right-side preview of definition JSON and metadata (version lock, timestamps).

- Studio (in‑app IDE)
  - Layout: center Monaco editor; left attachments (URLs/files/text) and Repo quick-pick; right Execution drawer (SSE traces, validation, cost).
  - Builder flow: Suggest → Propose → Apply; show questions/missing_fields; patch diff view; apply with optimistic lock.
  - Drafts: load/save/delete with `If-Match`; conflict message and reload helper.
  - Preview: run `/builder/preview/tool`; show output and logs; no network/FS.

- Canvas (visual editor)
  - Layout: React Flow canvas; toolbar for add nodes/auto-layout; bottom “Suggest an edit” input.
  - Nodes: tool/llm/agent/workflow/swarm; per-node validate/run; selection opens Inspector with JSON/edit links.
  - Execution: run full graph or single node; stream logs via SSE into Execution drawer; display status on nodes.

- Global interactions
  - Command palette (cmdk): navigate (canvas/studio/library), suggest, open component/blueprint, run preview.
  - Event telemetry: `ui.commandExecuted`, `builder.suggestRequested`, `canvas.nodeSelected`, `drafts.conflictDetected`, `preview.sandboxError`.
  - URL as state: tabs, filters, selected ids; deep linkable everywhere.

Quality Gates (function-first, styling later)
- Minimal Tailwind utilities now; tokens + shadcn/ui later for a11y and theme.
- Virtualize Repo grids when counts grow; debounce search; paginate server-side when needed.
- Vitest/Playwright: pane resize, Repo filters and open actions, Suggest → Apply happy path, SSE stream smoke.
