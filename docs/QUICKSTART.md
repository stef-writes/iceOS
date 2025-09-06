# iceOS Quickstart (No‑Code Hosted)

This Quickstart reflects the no‑code launch vision. End users sign up, upload content, and run workflows in the browser. No terminal, SDKs, or API keys are required.

## What a user does
- Visit the hosted Studio Lite.
- Sign up with email (magic link).
- Go to Library: upload files (docs/notes).
- Go to RAG Chat: ask questions; see answers with citations.
- Optionally view Components (names only) and Run History.

## What happens under the hood
- Frontend calls public REST endpoints on the API with bearer auth.
- Provider keys are stored server‑side only; the browser never sees them.
- Orchestrator executes validated workflows and returns results.

## Pages in the hosted app
- Library: upload, list, search your assets.
- RAG Chat: run the `chatkit.rag_chat` bundle; get answers/citations.
- Components: discover available tools/agents/workflows (names only).
- Runs: view run status and details.

---

## Appendix: Self‑Host & CLI (Developers)

The following section is for operators and developers. It is not required for no‑code end users.

## Prerequisites
- Docker + Docker Compose
- Set ICE_API_TOKEN (and provider keys if needed)

## Zero-setup (compose)
```bash
export ICE_API_TOKEN=dev-token
docker compose up -d postgres redis
docker compose run --rm migrate
docker compose up -d api
curl -s http://localhost:8000/readyz
```

## Start services (dev compose)
```bash
make demo-up && make demo-wait
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

## Personal Library (per-user assets)
```bash
# Add an asset
curl -s -H "Authorization: Bearer $ICE_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"label":"greeting","content":"hello world","mime":"text/plain","org_id":"demo_org","user_id":"demo_user"}' \
  http://localhost:8000/api/v1/library/assets

# List assets
curl -s -H "Authorization: Bearer $ICE_API_TOKEN" \
  'http://localhost:8000/api/v1/library/assets?org_id=demo_org&user_id=demo_user&limit=5'

# CLI equivalents
ice library add --label greeting --file README.md --mime text/plain --org demo_org --user demo_user
ice library list --org demo_org --user demo_user --limit 5
ice library get --label greeting --org demo_org --user demo_user
ice library rm --label greeting --org demo_org --user demo_user
```

## Memory-aware LLM (design note)
- Memory injection is handled by the orchestrator based on workflow design; no `memory_aware` field is required in node configs.

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
## Bundles and ChatKit (new)
Run a ready-made, reusable RAG chat Bundle with overrides:
```bash
ice bundle run chatkit \
  --file plugins/bundles/library_assistant/examples/fake_resume.txt \
  --note "focus skills" \
  --query "Summarize my background" \
  --session s1 \
  --model gpt-4o \
  --system "You are a helpful assistant."
```
Build a bundle artifact (optional):
```bash
ice bundle build plugins/bundles/chatkit
ls dist/bundles/
```
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

## Supabase Staging (Operators)

To verify against Supabase instead of local Postgres:

```bash
# Bring up API with staging override
export ICE_API_TOKEN=staging-admin-token
# Set DATABASE_URL inside docker-compose.staging.yml or via env-file

docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d api
curl -fsS http://localhost:8000/readyz

# Quick smoke
curl -fsS -X POST http://localhost:8000/api/v1/mcp/ \
  -H 'Authorization: Bearer staging-admin-token' \
  -H 'Content-Type: application/json' \
  -H 'X-Org-Id: demo_org' -H 'X-User-Id: alice' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"tool:memory_write_tool","arguments":{"inputs":{"key":"demo_key","content":"hello from staging","scope":"library"}}}}'

curl -fsS -X POST http://localhost:8000/api/v1/mcp/ \
  -H 'Authorization: Bearer staging-admin-token' \
  -H 'Content-Type: application/json' \
  -H 'X-Org-Id: demo_org' -H 'X-User-Id: alice' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"tool:memory_search_tool","arguments":{"inputs":{"query":"hello","scope":"library","limit":3}}}}'
```

Full guide: see `docs/STAGING.md`.
