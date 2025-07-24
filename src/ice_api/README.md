# ice_api – Spatial Computing API Gateway

## Purpose
`ice_api` exposes iceOS spatial computing functionality over HTTP + WebSocket.
It validates requests, translates them into **Workflow** executions with full spatial intelligence, and streams results back to clients with real-time canvas updates.

**🎯 Spatial Computing Features**
* **Graph Intelligence Endpoints** – NetworkX-powered analysis, optimization suggestions, and layout hints
* **Real-time Collaboration** – WebSocket streaming for canvas updates and cursor tracking  
* **Frosty Integration** – AI-powered contextual suggestions and workflow optimization
* **Blueprint Management** – Incremental construction with spatial metadata

Routes live under `ice_api.api.*` and are versioned (`/v1/...`).

## Quick-start (dev server)
```bash
uvicorn ice_api.main:app --reload
```

### Spatial Computing Endpoints
```http
# Execute workflow with spatial intelligence
POST /api/v1/mcp/runs
{
  "workflow_id": "spatial_demo",
  "input": { "query": "hello" },
  "enable_spatial_features": true
}

# Get graph metrics and layout hints
GET /api/v1/mcp/workflows/{workflow_id}/graph/metrics
GET /api/v1/mcp/workflows/{workflow_id}/graph/layout

# Analyze node impact for canvas updates  
GET /api/v1/mcp/workflows/{workflow_id}/nodes/{node_id}/impact

# Get Frosty AI suggestions
GET /api/v1/mcp/workflows/{workflow_id}/nodes/{node_id}/suggestions

# Find similar patterns for refactoring
POST /api/v1/mcp/workflows/{workflow_id}/graph/patterns
{
  "pattern_nodes": ["node1", "node2"]
}
```

## Architecture
```
Canvas UI ──► FastAPI (ice_api) ──► Workflow (ice_orchestrator) ──► ice_sdk/tools
     │                                   │
     └── WebSocket ←── Real-time ←── Spatial Events
```
* **Spatial Intelligence**: Workflow provides NetworkX-powered graph analysis and layout hints
* **Real-time Collaboration**: WebSocket gateway streams canvas updates, cursor positions, and execution events
* **Frosty Integration**: AI suggestions flow through the API for contextual canvas assistance
* Dependencies injected via `ice_api.dependencies` with spatial computing support

## Rules
* No direct DB or vectorstore access – delegate to Tool implementations.
* All external side-effects live in `ice_sdk.tools.*`.

## Testing
`pytest tests/api` runs contract & smoke tests.

## License
MIT. 