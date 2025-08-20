## Studio Flow: User Activities → Endpoints → Client Methods

This document maps common no-code Studio actions to the backend endpoints and the Python client methods.

### 1) Create new tool/agent from scratch
- UI action: New Component → select Tool | Agent
- Endpoint:
  - Scaffold: POST `/api/mcp/components/scaffold`
  - Register: POST `/api/mcp/components/register`
- Client:
  - `IceClient.scaffold_component(type, name, template=None)`
  - `IceClient.register_component(definition)`

### 2) Edit existing component
- UI action: Open component → edit → save
- Endpoint:
  - GET `/api/mcp/components/{type}/{name}` (reads `X-Version-Lock`)
  - PUT `/api/mcp/components/{type}/{name}` with `X-Version-Lock`
- Client:
  - `IceClient.get_component(type, name) -> (json, lock)`
  - `IceClient.update_component(type, name, definition, version_lock=lock)`

### 3) List components for palette
- UI action: Show available tools/agents/workflows
- Endpoint:
  - GET `/api/mcp/components`
  - GET `/api/mcp/components/{type}` (by type)
- Client:
  - `IceClient.list_components()`

### 4) Build blueprint incrementally
- UI action: Create draft → add/update/remove nodes → get suggestions
- Endpoint:
  - POST `/api/mcp/blueprints/partial`
  - GET `/api/mcp/blueprints/partial/{id}` (reads `X-Version-Lock`)
  - PUT `/api/mcp/blueprints/partial/{id}` with `X-Version-Lock`
  - POST `/api/mcp/blueprints/partial/{id}/suggest` (optional `commit` requires `X-Version-Lock`)
- Client:
  - `IceClient.create_partial_blueprint(initial_node=None)`
  - `IceClient.get_partial_blueprint(id) -> (json, lock)`
  - `IceClient.update_partial_blueprint(id, update, version_lock=lock)`
  - `IceClient.suggest_partial(id, top_k=5, allowed_types=None, commit=False, version_lock=None)`

### 5) Finalize and execute (standard path: MCP + SSE)
- UI action: Finalize draft → run workflow → watch events (SSE)
- Endpoint:
  - POST `/api/mcp/blueprints/partial/{id}/finalize` (requires `X-Version-Lock`)
  - POST `/api/mcp/runs` (accepts inline blueprint or `blueprint_id`)
  - GET `/api/mcp/runs/{run_id}/events` (SSE)
- Client:
  - `IceClient.finalize_partial_blueprint(id, version_lock=lock)`
  - `IceClient.submit_blueprint(blueprint_id=...) -> RunAck`
  - `async for e in IceClient.stream_events(run_id)`: consume SSE live
  - `await IceClient.wait_for_completion(run_id)` for final result

#### Studio convenience helpers
- `await IceClient.run_and_wait(blueprint=..., blueprint_id=...)` – finalize (if needed), submit, and wait.
- `async for evt in IceClient.run_and_stream(blueprint=..., blueprint_id=...)` – finalize (if needed), submit, and stream SSE.

Note: Agent nodes must declare minimal schemas to pass validation. Example:
```json
{
  "id": "agent1",
  "type": "agent",
  "package": "demo_agent",
  "input_schema": {"message": "str"},
  "output_schema": {"reply": "str"}
}
```

Note: The Executions API (`/api/v1/executions` + WebSocket) remains available
for programmatic integrations; Studio defaults to the MCP + SSE path.

### 6) Not BYOK posture
- The server reads provider API keys from environment only; client requests must not include `api_key`.
- Agent compose helper enforces this by stripping `api_key` if present.
