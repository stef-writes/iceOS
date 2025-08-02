# ice_api – API Gateway

## Purpose
`ice_api` exposes iceOS functionality over HTTP + WebSocket. It validates requests, translates them into **Workflow** executions via the orchestrator layer, and streams results back to clients.

**🎯 Core Features**
* **MCP Protocol** – Model Context Protocol for blueprint management and execution
* **Direct Execution** – Quick endpoints for single tool/agent/workflow execution
* **Event Streaming** – Real-time execution events via SSE
* **Blueprint Management** – Register and execute workflows (Frosty will consume these endpoints)
* **Redis Integration** – Event streaming and blueprint persistence

Routes live under `ice_api.api.*` and are versioned (`/api/v1/...`).

### Frosty Integration 🧊
The `/api/v1/blueprints` and `/api/v1/executions` endpoints are now consumed by
[Frosty](../frosty/README.md) – the code-generation layer that turns natural
language into runnable workflows. A full round-trip looks like this:

```bash
make dev-up                    # start Redis + API in background

# 1) Generate blueprint from NL prompt
poetry run frost generate "say hello to Ada" --provider o3
#    └─ Frosty calls /blueprints → returns <bp_id>
# 2) Execution is started automatically → streams status until completion
```

The same endpoints power the `ice push` and `ice run` CLI commands for manual
workflow deployment and execution.

### FastAPI Dev Server
```bash
poetry run uvicorn ice_api.main:app --reload
```

Below are the most commonly used MCP endpoints (full OpenAPI spec at `/docs`).

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

# Execute a workflow node
POST /api/v1/workflows/{workflow_name}/execute
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
GET /api/v1/workflows # List all workflows  
GET /api/v1/chains    # List all chains
```

Response includes:
- `run_id` - Track execution progress
- `status` - "completed", "running", or "failed"
- `output` - Execution results
- `telemetry_url` - Event stream URL

### MCP Blueprint Endpoints
```http
# Register blueprint (full)
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
Client ──► FastAPI ──► Orchestrator ──► Runtime Services
         (ice_api)   (ice_orchestrator)  │
            │                            ├─► Agents
            │                            ├─► Memory
            └── Events ←── Execution ────┴─► LLM Services
                          Events
```

* **MCP Protocol**: Standard interface for workflow management
* **Hybrid Execution**: Direct endpoints create single-node blueprints internally
* **Event Streaming**: Server-sent events via Redis for real-time updates
* **Service Injection**: Dependencies injected via `ice_api.dependencies`

## Layer Interactions

The API layer:
1. Receives HTTP/WebSocket requests
2. Validates and transforms them into workflow configurations
3. Delegates execution to `ice_orchestrator`
4. Streams back events and results

Key dependencies:
- `ice_orchestrator.workflow.Workflow` - Main workflow execution
- `ice_orchestrator.context.GraphContextManager` - Context management
- `ice_core.unified_registry` - Component discovery
- Redis - Event streaming and blueprint storage

## Rules
* No direct business logic – purely API translation layer
* All execution happens in orchestrator layer
* No direct tool/agent implementation access
* Layer boundaries strictly enforced

## Testing
```bash
pytest tests/integration/ice_api  # Integration tests
pytest tests/unit/ice_api         # Unit tests
```

## License
MIT 