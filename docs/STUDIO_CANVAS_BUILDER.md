AI Builder integration (Studio & Canvas)

Scope: minimal backend-first integration for the co‑creator. This guide shows how Studio/Canvas can call the Builder endpoints, surface Q/A and cost, save drafts, and preview code safely.

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
