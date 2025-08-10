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

- `POST /api/v1/blueprints/` create/update with version lock
- `POST /api/v1/executions/` start run (budget preflight enforced)
- `GET /api/v1/meta/nodes` catalog (tools/agents/workflows)
- `POST /api/mcp` JSON-RPC methods (components/validate, tools/list, network.execute)