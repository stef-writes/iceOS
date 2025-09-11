# ice_api – REST + MCP API Gateway

FastAPI app that implements the compile-time (MCP) and runtime (executions) tiers.

## Quick start (Docker Compose)

```bash
docker compose up --build -d api redis
```

Required env (compose sets reasonable defaults):

- `ICE_API_TOKEN` (dev default: `dev-token`)
- Provider keys as needed: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`
- `ICE_ENABLE_WASM=1` (default) to enable code-node execution via WASM

## Deterministic one-shot run

Start an execution and return the final result in a single call using `wait_seconds`.

```bash
curl -sS -X POST "http://localhost/api/v1/executions/?wait_seconds=10" \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' \
  -d '{"payload": {"blueprint_id":"<bp_id>","inputs":{}}}'
```

The `wait_seconds` parameter is defined on the route:

```195:203:src/ice_api/api/executions.py
async def start_execution(
    request: Request,
    payload: Dict[str, Any] = Body(..., embed=True),
    wait_seconds: float | None = Query(
        default=None,
        description=(
            "Optional: block up to N seconds and return final status/result instead of an execution_id."
        ),
    ),
```

## Verified MCP authoring flow (tool → partial blueprint → finalize → run)

1) Validate/register a tool factory

```bash
curl -sS -X POST http://localhost/api/mcp/components/validate \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' \
  -d '{"type":"tool","name":"demo_text_upper","description":"Uppercases input text.","tool_factory_code":"from typing import Any, Dict\nfrom ice_core.base_tool import ToolBase\n\nclass UppercaseTool(ToolBase):\n    name: str = \"demo_text_upper\"\n    description: str = \"Uppercases input text.\"\n\n    async def _execute_impl(self, text: str) -> Dict[str, Any]:\n        return {\"result\": text.upper()}\n\n\ndef create_demo_text_upper() -> UppercaseTool:\n    return UppercaseTool()\n","auto_register": true,"validate_only": false}'
```

2) Create a partial blueprint, add nodes, finalize

```bash
PB_ID=$(curl -sS -X POST http://localhost/api/mcp/blueprints/partial -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' -d 'null' | sed -n 's/.*"blueprint_id":"\([^"]\+\)".*/\1/p')
LOCK=$(curl -sS -X GET http://localhost/api/mcp/blueprints/partial/$PB_ID -H 'Authorization: Bearer dev-token' -i | tr -d '\r' | awk '/^x-version-lock:/ {print $2}')
curl -sS -X PUT http://localhost/api/mcp/blueprints/partial/$PB_ID \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' -H "X-Version-Lock: $LOCK" \
  -d '{"action":"add_node","node":{"id":"to_upper","type":"tool","dependencies":[],"tool_name":"demo_text_upper","tool_args":{"text":"hello world"}}}'
LOCK=$(curl -sS -X GET http://localhost/api/mcp/blueprints/partial/$PB_ID -H 'Authorization: Bearer dev-token' -i | tr -d '\r' | awk '/^x-version-lock:/ {print $2}')
curl -sS -X PUT http://localhost/api/mcp/blueprints/partial/$PB_ID \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' -H "X-Version-Lock: $LOCK" \
  -d '{"action":"add_node","node":{"id":"llm1","type":"llm","dependencies":["to_upper"],"model":"gpt-4o","llm_config":{"provider":"openai","model":"gpt-4o","max_tokens":64,"temperature":0.2},"prompt":"Uppercased: {{ to_upper.result }}"}}'
LOCK=$(curl -sS -X GET http://localhost/api/mcp/blueprints/partial/$PB_ID -H 'Authorization: Bearer dev-token' -i | tr -d '\r' | awk '/^x-version-lock:/ {print $2}')
BP_ID=$(curl -sS -X POST http://localhost/api/mcp/blueprints/partial/$PB_ID/finalize -H 'Authorization: Bearer dev-token' -H "X-Version-Lock: $LOCK" | sed -n 's/.*"blueprint_id":"\([^"]\+\)".*/\1/p')
```

3) Execute and wait for the result

```bash
curl -sS -X POST "http://localhost/api/v1/executions/?wait_seconds=10" \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' \
  -d '{"payload": {"blueprint_id":"'"$BP_ID"'","inputs":{}}}'
```

Example response (truncated):

```json
{"status":"completed","result":{"success":true,"output":{"to_upper":{"result":"HELLO WORLD"},"llm1":{"response":"Lowercased: hello world","prompt":"Uppercased: HELLO WORLD","model":"gpt-4o","usage":{"total_tokens":20}}}}}
```

## Health routes

- `GET /livez` – process liveness
- `GET /readyz` – readiness after startup
- `GET /health` – Redis connectivity

## Notes

- Code nodes require `ICE_ENABLE_WASM=1` and `wasmtime` present; otherwise 400/RuntimeError.
- Provider health is logged at startup; compile-time checks will be enforced during MCP validation/finalize.
