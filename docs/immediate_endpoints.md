# Immediate API Endpoints

This document specifies the **minimal FastAPI surface** required for the first interactive demos (CLI, infinite-canvas editor, "Frosty" text-to-chain).  Implement these endpoints before any UI work begins.

## 1. Service Health
| Method | Path   | Purpose                |
|--------|--------|------------------------|
| GET    | /health | Simple `{"status": "ok"}` to verify the server is alive.

## 2. Catalog / Discovery (read-only)
Exposes the library of building blocks so the front-end can populate a palette.

| Method | Path                | Description |
|--------|---------------------|-------------|
| GET    | /catalog/nodes      | List available node classes.  Each item includes name, description, and JSON schema for parameters.
| GET    | /catalog/tools      | List all tools with their JSON schema.
| GET    | /catalog/agents     | List all agent classes with their JSON schema.

*Implementation notes*
- The data comes from the runtime registries in `ice_sdk` (no database needed).
- Response model: `List[CatalogItem]`, where `CatalogItem` is a Pydantic model with fields `name`, `kind` (`node`\|`tool`\|`agent`), `schema` (dict), `description`.

## 3. ScriptChain CRUD & Execution
Chains are the only *mutable* entity for the MVP. Nodes are embedded inside chains, so separate node CRUD is not needed.

| Method | Path                           | Description |
|--------|--------------------------------|-------------|
| GET    | /chains                        | List all saved ScriptChains (`id`, `name`). |
| POST   | /chains                        | Create a new chain. Body = JSON or YAML. Returns created chain with `id`. |
| GET    | /chains/{chain_id}             | Retrieve full chain definition. |
| PUT    | /chains/{chain_id}             | Replace definition (idempotent update). |
| DELETE | /chains/{chain_id}             | Delete chain. |
| POST   | /chains/{chain_id}/run         | Execute once, wait for completion, return final node outputs. |

*Implementation notes*
- Storage layer can be an **in-memory dict** keyed by UUID. Swap for DB later.
- Use existing `ScriptChain.from_dict()` for validation.
- `POST /chains/:id/run` should accept optional `input` payload (dict) and return `{ "result": Any, "logs": List[NodeLog] }`.

## 4. Future (not in MVP, but reserved)
| Path                          | Purpose |
|--------------------------------|---------|
| /chains/{id}/run/stream        | WebSocket for live node events. |
| /runs, /runs/{run_id}          | Persisted execution history. |
| /ai/draft-chain                | "Frosty" endpoint: NL → ScriptChain JSON. |

---
*Last updated*: {{DATE}} 