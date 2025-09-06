# End-to-end story (grounded in current code)
> Vision summary (from the former vision_happy_path.md): Repo Hub is SSOT; Studio is the compile tier; Canvas is the design-time tier; MCP validates and registers; the Orchestrator executes blueprints with SSE events. Strict-edge contracts at REST/Blueprint; lenient bus at runtime for composability.

This story follows the exact APIs and flows present in this repo today. It avoids assumptions and only references implemented endpoints and models.

## 0) Preconditions
- API started with Bearer auth enabled; optional plugin manifests loaded (to show built-ins in Repo).
- Frontend uses NEXT_PUBLIC_API_URL/token and the local @ice/api-client (built first).

## 1) Discover assets in Library → Repo
- UI calls `GET /api/v1/library/assets/index?kind=component` to list components and `?kind=blueprint` to list blueprints (see `ice_api/api/library.py`).
- The grid shows NodeCards with actions:
  - Open → navigates to Studio: `/studio?type={tool|agent|workflow|code}&name={...}` or `/studio?blueprintId={id}`.
  - Canvas → navigates to `/canvas?...` (graph rendering is basic for now).
  - Copy ID → copies `name` or `blueprint id`.

## 2) Inspect/edit in Studio (IDE)
- When `type`/`name` are present, Studio loads the component via `GET /api/v1/mcp/components/{type}/{name}` (see `ice_api/api/mcp.py`) and displays JSON in Monaco.
- When `blueprintId` is present, Studio loads it via `GET /api/v1/mcp/blueprints/{id}`.
- The Builder panel exposes the co‑creator MVP:
  - Suggest: `POST /api/v1/builder/suggest` with `{text, canvas_state, provider?, model?, temperature?}` (see `ice_api/api/builder_mcp.py`).
  - The response includes `patches`, `questions`, `missing_fields`, and optional `cost_estimate_usd`.
- Drafts:
  - Save/edit in‑progress JSON via `PUT /api/v1/builder/drafts/{key}` (If‑Match concurrency header supported) and `GET/DELETE` for load/remove (see `ice_api/api/builder_drafts.py`).

## 3) Safe code preview (no side effects)
- Studio can preview a code node using `POST /api/v1/builder/preview/tool` (see `ice_api/api/builder_preview.py`).
- The endpoint executes in a WASM-only sandbox; disallows imports outside the allowlist; returns `{success, output, error, logs}`.

## 4) Build a partial blueprint with the Builder
- For incremental design, the API supports PartialBlueprints in MCP (`ice_api/api/mcp.py`):
  - `POST /api/v1/mcp/blueprints/partial` → create
  - `PUT /api/v1/mcp/blueprints/partial/{id}` with `X-Version-Lock` → update
  - `POST /api/v1/mcp/blueprints/partial/{id}/suggest` → deterministic suggestions
  - `POST /api/v1/mcp/blueprints/partial/{id}/finalize` with `X-Version-Lock` → finalize to a `blueprint_id`
- The frontend currently exposes Suggest (MVP). Propose/Apply wiring can be layered on using `/api/v1/builder/propose|apply`.

## 5) Run a stored blueprint and stream status
- Start a run via `POST /api/v1/mcp/runs` with either `blueprint_id` or an inline blueprint (see `ice_api/api/mcp.py`).
  - The response includes `run_id`, `status_endpoint`, and `events_endpoint`.
  - The Execution Drawer subscribes to SSE at `GET /api/v1/mcp/runs/{run_id}/events` and prints events/logs.
- Alternatively, the Executions API (DB‑backed) exists at `POST /api/v1/executions/` and `GET /api/v1/executions/{execution_id}` (see `ice_api/api/executions.py`). This path is available for programmatic use or future UI wiring.

## 6) Persist components for reuse (Repo)
- Components are validated/registered through `/api/v1/mcp/components/validate` and `/api/v1/mcp/components/register` (see `ice_api/api/mcp.py`).
- Library → Repo lists the stored/registered assets via the unified index and the MCP components routes.

## 7) Knowledge (user assets)
- Knowledge items use `/api/v1/library/assets` to create/list/delete text content; these live in semantic memory with `scope="library"` (see `ice_api/api/library.py`).

## 8) Telemetry and URL-as-state (frontend)
- Events to emit (names enforced in code): `ui.commandExecuted`, `builder.suggestRequested`, `canvas.nodeSelected`, `drafts.conflictDetected`, `preview.sandboxError`.
- The App Router encodes filters and selections in URLs so every surface is deep-linkable.

This narrative mirrors the exact implementation and leaves styling/theme decisions for a later pass.
