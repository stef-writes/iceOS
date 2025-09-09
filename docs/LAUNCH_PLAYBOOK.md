# Launch Playbook (AI‑native, no‑code)

This is the single source of truth to run, verify, and demo the app end‑to‑end after a cold start.

## 0) Scope and success criteria
- Frontend (Next.js) serves workflows, templates, execution status, Library, and Frosty (copilot) from a single origin (:3000).
- Backend (FastAPI) is healthy on :8000; CORS and trusted hosts correct; budgets enforced.
- Plugins and built‑in bundles are discoverable; from‑workflow materialization works.
- Founder Demos (below) all pass via the frontend origin.
- Type/lint pass; integration demo lane green (no host port binds; clean exit).

## 1) Bringup (local)
- One‑time migrations:
```bash
docker compose run --rm migrate
```
- Start stack:
```bash
make demo-live
```
- Health:
```bash
curl -fsS http://localhost:3000/readyz
curl -fsS http://localhost:8000/readyz
```

## 2) Founder Demos (via frontend origin)
- Templates → Blueprint → Execute
  - List: GET /api/v1/templates/
  - Materialize: POST /api/v1/templates/from-workflow { workflow_id: chatkit.rag_chat }
  - Execute with wait: POST /api/v1/executions/?wait_seconds=20
  - Success: 200/201; status=completed; non‑empty result.

- Ask My Library (RAG)
  - Seed asset: POST /api/v1/library/assets (label/content)
  - Materialize library_assistant.ask_my_library; execute with query.
  - Success: completed; response includes a citation (asset label/key) and <=512 tokens.

- Web search → summarize
  - Draft workflow: search tool feeding LLM; temperature 0.2.
  - Success: completed; includes ≥1 URL and 3–5 bullets.

- CSV mini‑pipeline
  - Ingest 3–5 row CSV; transform; write JSON summary.
  - Success: completed; JSON list; summary object includes count and basic stats.

- Frosty (Agent plan preview)
  - POST /api/v1/frosty/suggest_v2 with text + canvas_state.
  - Show steps, inputs, and cost; approve → executions run completes.
  - Success: patches present; validate/simulate succeed; run plan estimates cost; execution completed.

- Multi‑workspace isolation
  - Two projects; assets only in A.
  - Success: A run sees assets; B run does not; cross‑access blocked.

## 3) Frontend alignment
- Workflow overview cards (type, nodes, last run, cost). Click → Canvas with blueprintId.
- Execution drawer: live node events, durations, cost; cancel/retry; result viewer.
- Agent plan preview (Frosty): steps+cost; inline edit; approve to run.
- Library uploads: drag/drop; progress; list recent; attach to project.
- Knowledge retrieval: scope chips; confidence; open asset sidebar; citation toggle.
- Model/budget controls: allowed models only; temperature/tokens; preflight budget bar.
- Errors: 422 field hints; 402 downgrade suggestion; network retry.
- Context: topbar workspace/project switch; X-Project-Id auto‑injected.
- Demo recorder: “Save as Founder Demo” stores inputs/outputs/latency; one‑click replay.

## 4) Plugins & bundles
- Manifests loaded from ICEOS_PLUGIN_MANIFESTS (memory/search; chatkit; getting_started).
- Verify: GET /api/v1/templates/ shows entries; from‑workflow resolves paths; executing built‑ins succeeds.

## 5) Storage modes
- Local Postgres + pgvector (default): migrations reach head; /api/v1/meta/storage reports backend ready.
- Staging (Supabase): make stage-up as needed; same demos run against staging URL.

## 6) CI/demo lane
- Type/lint: make ci
- Integration demo lane: make ci-integration (no Redis host binding; clean runner exit).
- Optional nightly: run Founder Demos; store success rate, p95 latency, token/$.

## 7) Operational notes
- Keys: OPENAI_API_KEY required; others optional. ICE_API_TOKEN dev-token in local.
- Trusted hosts/CORS: locked to dev hostnames; widen only for staging/prod domains.
- Budgets: ORG_BUDGET_USD enforced; preflight blocks excessive models.

## 8) Success checklist for launch
- All Founder Demos pass via frontend origin with live models.
- Type/lint green; integration demo lane exits 0.
- Docs in docs/VERIFICATION_PLAYBOOK.md and this playbook are accurate.
- Docker Desktop minimal state: single builder; no dangling images; compose orphans cleaned.

## 9) Structure guidance (no big reshape pre‑launch)
- Keep backend as‑is under `src/` (`ice_api`, `ice_orchestrator`, `ice_core`) – layer boundaries already strong.
- Keep frontend at `frontend/apps/web`; all HTTP via `frontend/packages/api-client` only.
- Optional light additions:
  - `frontend/packages/ui` for shared components (Card, Table, Drawer, Badge, ModelPicker, CostChip)
  - Feature modules in `apps/web/modules/{workflows,templates,library,runs,frosty}`
- Post‑launch triggers for larger moves: multiple web apps, separate marketing site, or new backend services.

## 10) Frontend 20/80 backlog (low‑hanging, high value)
- Workflow overview cards: type badge, node count, last run status/time, cost; click → Canvas.
- Execution drawer: live node events, durations, cost; cancel/retry; result viewer.
- Templates: gallery → materialize → auto‑route to Canvas; show cost estimate.
- Library uploads: drag/drop with progress; list recent; attach to project.
- RAG chat: citation chips linking to assets; “Use my library” toggle; session selector.
- Model/budget controls: allowed models only; temperature/tokens; preflight budget messages.
- Errors/toasts: 422 field hints; 402 downgrade CTA; network retry.
- Context: always‑visible workspace/project switch; verify `X-Project-Id` on all requests.
- Demo recorder: Save + replay Founder Demos with artifacts (inputs/outputs/latency).
