# Staging (Supabase) Setup and Verification

This doc describes how to run iceOS API against Supabase (transaction pooler) and verify core functionality.

## Prerequisites
- Supabase project with credentials
- Transaction Pooler DSN (port 6543)
- Admin bearer token for API (ICE_API_TOKEN)

## Environment

Use the staging compose override to ensure clean env isolation:

- `docker-compose.staging.yml` overrides API env and sets:
  - `ICEOS_RUN_MIGRATIONS=0`, `ICEOS_REQUIRE_DB=0`
  - `DATABASE_URL=postgresql+asyncpg://...:6543/postgres`
  - `ALEMBIC_SYNC_URL=postgresql://...:6543/postgres?sslmode=require`
  - `ICE_MCP_DEFAULT_TIMEOUT=90`, `ICE_TOOL_DEFAULT_TIMEOUT_SECONDS=90`, `ICE_TOOL_DEFAULT_RETRIES=1`

## Bring up API

```bash
# ensure docker is running
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d api
curl -fsS http://localhost:8000/readyz
```

## Smoke Tests

- Memory (MCP):
```bash
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

- Library CRUD (REST):
```bash
curl -fsS -X POST http://localhost:8000/api/v1/library/assets \
  -H 'Authorization: Bearer staging-admin-token' \
  -H 'Content-Type: application/json' \
  -H 'X-Org-Id: demo_org' -H 'X-User-Id: alice' \
  -d '{"label":"smoke1","content":"hello library asset","mime":"text/plain","scope":"library"}'
```

## Integration Tests

- Fast subset against running API:
```bash
# start api (if not already)
docker compose -f docker-compose.itest.yml -f docker-compose.itest.staging.yml up -d api
# run key tests
docker compose -f docker-compose.itest.yml run --rm itest bash -lc "pytest -q -k 'test_memory_write_and_semantic_search_via_mcp or test_library_add_list_get_delete or test_ask_my_library_end_to_end' -c config/testing/pytest.ini"
```

- Full Supabase-backed suite (optional):
```bash
make ci-integration-staging DATABASE_URL='postgresql+asyncpg://<user>:<pass>@aws-0-us-east-2.pooler.supabase.com:6543/postgres'
```

## Notes
- asyncpg DSN must NOT include `?sslmode=require`. For migrations, use `ALEMBIC_SYNC_URL` with `psycopg2` and `sslmode=require`.
- Timeouts/retries are environment-configurable in MCP handler and tool nodes for staging latency.
