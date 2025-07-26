# ice_api – API Gateway

## Purpose
`ice_api` exposes iceOS functionality over HTTP + WebSocket.
It validates requests, translates them into **Workflow** executions, and streams results back to clients.

**🎯 Core Features**
* **MCP Protocol** – Model Context Protocol for blueprint management and execution
* **Direct Execution** – Quick endpoints for single tool/agent/unit/chain execution
* **Event Streaming** – Real-time execution events via SSE
* **Blueprint Management** – Register and execute workflows

Routes live under `ice_api.api.*` and are versioned (`/api/v1/...`).

## Quick-start (dev server)
```bash
uvicorn ice_api.main:app --reload
```

### Direct Execution Endpoints
For quick testing and experimentation, use these direct execution endpoints:

```http
# Execute a tool directly
POST /api/v1/tools/{tool_name}
{
  "inputs": { "file_path": "data.csv" },
  "wait_for_completion": true,
  "timeout": 30.0
}

# Execute an agent  
POST /api/v1/agents/{agent_name}
{
  "inputs": { "query": "analyze this data" }
}

# Execute a unit
POST /api/v1/units/{unit_name}
{
  "inputs": { "data": [...] }
}

# Execute a chain
POST /api/v1/chains/{chain_name}
{
  "inputs": { "context": {...} }
}

# Discovery endpoints
GET /api/v1/tools     # List all tools
GET /api/v1/agents    # List all agents
GET /api/v1/units     # List all units  
GET /api/v1/chains    # List all chains
```

Response includes:
- `run_id` - Track execution progress
- `status` - "completed", "running", or "failed"
- `output` - Execution results
- `telemetry_url` - Event stream URL

### MCP Blueprint Endpoints
```http
# Register blueprint
POST /api/v1/mcp/blueprints
{
  "blueprint_id": "my_workflow",
  "nodes": [
    {
      "id": "analyze",
      "type": "llm",
      "model": "gpt-4",
      "prompt": "Analyze this: {input}",
      "llm_config": {
        "provider": "openai",
        "model": "gpt-4"
      }
    }
  ]
}

# Execute blueprint/workflow
POST /api/v1/mcp/runs
{
  "blueprint_id": "my_workflow",
  "inputs": {"input": "test data"},
  "options": {
    "max_parallel": 2,
    "retry_failed": true
  }
}

# Get execution status
GET /api/v1/mcp/runs/{run_id}

# Stream execution events
GET /api/v1/mcp/runs/{run_id}/events
```

## Architecture
```
Client ──► FastAPI (ice_api) ──► Workflow (ice_orchestrator) ──► ice_sdk/tools
            │                         │
            └── Events ←── Execution Events
```
* **MCP Protocol**: Standard interface for workflow management
* **Hybrid Execution**: Direct endpoints create single-node blueprints internally
* **Event Streaming**: Server-sent events for real-time updates
* Dependencies injected via `ice_api.dependencies`

## Rules
* No direct DB or vectorstore access – delegate to Tool implementations
* All external side-effects live in `ice_sdk.tools.*`
* Layer boundaries strictly enforced

## Testing
`pytest tests/api` runs contract & smoke tests.

## License
MIT 