# Frosty (Copilot) – Read/Write/Plan Roadmap

Goal: production-grade copilot that translates text → actionable graph edits and run plans, with correct project/workspace context, guardrails, and observability. Surfaced in the frontend, backed by `/api/v1/frosty/*`.

## Current signals in repo
- Backend routes: `src/ice_api/api/frosty_actions.py` (`/api/v1/frosty/suggest_v2`, `validate`, `simulate`, `run_plan`).
- Frontend entry: `apps/web/modules/frosty/CopilotPanel.tsx` calls `suggest_v2` via `modules/frosty/api/client.ts`.
- Event telemetry hooks exist (see `modules/core/events`).

## Gaps to close
1) Context fidelity
- Inject `X-Project-Id` automatically in all copilot calls (already done via `modules/api/client.ts` fetch wrapper). Verify end-to-end.
- Ensure copilot requests include current `blueprint_id` and canvas state (nodes, selections) when available.

2) Read: accurate source of truth
- Read node catalogs via `/api/v1/meta/nodes/*` and templates via `/api/v1/templates/` for schema-aware suggestions.
- Add lightweight “canvas snapshot” endpoint (optional) or standardize payload shape in `suggest_v2` to include minimal canvas state.

3) Write: safe edits
- Use `validate` and `simulate` routes to dry-run patches; only apply if validation passes.
- Enforce optimistic locks via `X-Version-Lock` when mutating blueprints (copilot should fetch, patch, then PUT with lock).

4) Plan & Execute
- `run_plan`: produce explicit node-level plan (ids, order, inputs) with cost estimate; stream progress via events in executions API.
- Frontend: present plan preview (diff + cost) and confirm before execution.

5) Guardrails
- Budget preflight: reject plans above threshold with actionable downgrade suggestions.
- Schema validation: fail-fast with precise field-level errors mapped to UI highlights.

6) Observability
- Emit `frosty.suggestRequested`, `frosty.actionsApplied`, `frosty.runRequested` consistently.
- Backend: structured logs with project_id, blueprint_id; persist minimal audit trail.

## Acceptance tests (frontend-driven)
- Suggest: Free-text → non-empty `patches` and/or `questions`; no 5xx.
- Validate+Simulate: invalid patch returns clear errors; valid patch returns updated blueprint preview.
- Run plan: returns steps and cost; confirm → execution completes successfully.
- Multi-project: suggestions respect `X-Project-Id`; cannot mutate outside project.

## Minimal API contract for suggest_v2
```json
{
  "text": "add a tool that searches the web for 'ACME news' and feed into llm",
  "canvas_state": { "selected": ["n2"], "nodes": [] },
  "provider": "openai",
  "model": "gpt-4o",
  "temperature": 0.2
}
```
Response
```json
{
  "patches": [],
  "questions": ["Which model family do you prefer?"],
  "missing_fields": { "llm_config.model": ["required"] },
  "cost_estimate_usd": 0.002
}
```

## Next implementation steps
- Backend: tighten `frosty_actions.suggest_v2` to pull node schemas and generate targeted patches; add `validate` and `simulate` logic using builder/orchestrator validators.
- Frontend: wire CopilotPanel to display questions, patch preview, and plan confirmation; then call `executions` on confirm.
- Add `docs/VERIFICATION_PLAYBOOK.md` checks for Frosty (suggest → simulate → run plan → execute).

## Done =
- Reproducible end-to-end: type text → patches preview → apply → plan → execute → result, all from frontend.
- Logs clean, no 5xx, budget preflight enforced, schemas validated.
