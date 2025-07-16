# ice_api – FastAPI Service Layer

## Purpose
`ice_api` exposes IceOS functionality over HTTP + WebSocket.
It validates requests, translates them into `ScriptChain` executions via the
**Orchestrator**, and streams results back to clients.

Routes live under `ice_api.api.*` and are versioned (`/v1/...`).

## Quick-start (dev server)
```bash
uvicorn ice_api.main:app --reload
```

```http
POST /v1/chains/execute
{
  "chain_id": "demo",
  "input": { "query": "hello" }
}
```

## Architecture
```
Client ──► FastAPI (ice_api) ──► ice_orchestrator ──► ice_sdk/tools
```
* Dependencies injected via `ice_api.dependencies`.
* WebSocket gateway (`ws_gateway.py`) streams incremental node results.

## Rules
* No direct DB or vectorstore access – delegate to Tool implementations.
* All external side-effects live in `ice_sdk.tools.*`.

## Testing
`pytest tests/api` runs contract & smoke tests.

## License
MIT. 