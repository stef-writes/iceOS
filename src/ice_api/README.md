# ice_api – REST + MCP API Gateway

FastAPI application exposing:

- REST endpoints for blueprints, executions, discovery, registry health
- MCP JSON-RPC endpoint under `/api/mcp`
- WebSocket endpoints for drafts and execution streaming

Startup summary:

- On process start, the app imports `ice_orchestrator` and calls `initialize_orchestrator()`
- Orchestrator wires runtime slots in `ice_core.runtime` and loads first-party tools via an explicit plugin loader

Local dev:

```bash
uvicorn ice_api.main:app --reload --port 8000
```

Auth:

- Bearer token `dev-token` in dev profile (see `ice_api.security`)

Key routes:

- Blueprints (REST):
  - `POST /api/v1/blueprints/` create (requires `X-Version-Lock: __new__`)
  - `GET|PATCH|PUT|DELETE /api/v1/blueprints/{id}` CRUD with optimistic version lock
- Executions (REST):
  - `POST /api/v1/executions/` start run (budget preflight enforced)
  - `GET /api/v1/executions/{id}` status; `POST /api/v1/executions/{id}/cancel`
- MCP (Compiler-tier REST):
  - `POST /api/v1/mcp/components/validate` validate and (optionally) register components
  - `POST /api/v1/mcp/components/scaffold` scaffold code for tools/agents
  - `POST /api/v1/mcp/components/register` persist + register components
  - `GET /api/v1/mcp/components` list stored + registered components
  - `GET|PUT|DELETE /api/v1/mcp/components/{type}/{name}` CRUD (uses `X-Version-Lock`)
  - `POST /api/v1/mcp/agents/compose` compose an agent (not BYOK)
  - Partial blueprints: `POST /blueprints/partial`, `GET|PUT /blueprints/partial/{id}`,
    `POST /blueprints/partial/{id}/finalize`, `POST /blueprints/partial/{id}/suggest`
- MCP JSON-RPC: `/api/mcp` (components/validate, tools/list, network.execute)
- WebSockets: `/ws/mcp`, `/ws/drafts/{session_id}`, `/ws/executions/{execution_id}`
