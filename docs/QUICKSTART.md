# iceOS Quickstart

## Prerequisites
- Docker + Docker Compose
- Set ICE_API_TOKEN (and provider keys if needed)

## Start services (compose)
```bash
make ci-integration
```

## Push and run a workflow (CLI)
```bash
export ICE_API_URL=http://localhost:8000
export ICE_API_TOKEN=dev-token
ice push examples/hello_world.json
ice run --last
```

## Upload and search documents (CLI)
```bash
ice uploads files --files README.md --scope kb
ice memory write --key doc1 --content "hello world" --scope kb
ice memory search --query "hello" --scope kb --top-k 3
```

## MCP tools via Postman
- Import config/postman/iceos.postman_collection.json
- Set baseUrl and apiToken
- Call MCP initialize then tools/call

## Health & registry
```bash
curl -s http://localhost:8000/readyz | jq
ice registry summary
```

## WASM (optional)
```bash
# Enable per environment and run wasm-only tests
make ci-wasm
```

## Stress suite (ResourceSandbox; optional)
```bash
# Run heavy stress test locally
IMAGE_REPO=local IMAGE_TAG=dev ICE_SKIP_STRESS=0 \
  docker compose -f docker-compose.itest.yml run --rm itest \
  bash -lc 'pytest -c config/testing/pytest.ini -q tests/integration/ice_orchestrator/test_resource_sandbox.py'
```

## DSL Builder (preview & resolvability)
```python
from ice_builder.dsl.workflow import WorkflowBuilder

b = WorkflowBuilder("demo").add_tool("t1", tool_name="writer_tool")
print(b.preview())  # Mermaid diagram
issues = b.validate_resolvable()
assert not issues, issues
```

## Python client (submit → wait/stream)
```python
import asyncio
from ice_client import IceClient

async def main():
    async with IceClient("http://localhost:8000") as client:
        # Submit an existing blueprint by id
        ack = await client.submit_blueprint(blueprint_id="bp_demo")
        result = await client.wait_for_completion(ack.run_id)
        assert result.success

asyncio.run(main())
```
