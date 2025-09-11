## iceOS Verification Playbook (Current State)

### What’s in place
- **DB (Postgres)**: Authoritative storage for blueprints, executions, execution_events, tokens, semantic_memory, workspaces, projects, mounts. Alembic migrations are out-of-band and verified.
- **Redis**: Used for caching/streaming and chat session state (ephemeral). No fake/inline Redis.
- **API (FastAPI)**: Clean startup (no in-app migrations). Single readiness gate `/readyz` checks startup flag and Redis ping.
- **Chat**: Agent-first execution path via AgentNodeConfig (with LLM fallback), persists transcripts to `semantic_memory` (scope="chat").
- **Frosty**: Typed endpoints; telemetry to `semantic_memory` (scope="frosty").
- **Uploads**: Ingestion tool persists chunks and embeddings to `semantic_memory`.
- **Tests**: Integration tests for uploads, chat, frosty, blueprint CRUD are green. DB sessions are context-managed; engine disposal eliminates teardown warnings.

### Expected behavior (dev)
- `make dev-db` brings up Postgres and Redis.
- `make dev-migrate` applies Alembic to head against compose Postgres.
- `make dev-api` starts API and waits for `/readyz` (<=120s) or tails logs on failure.
- `make fe-dev` starts Next.js dev UI at `http://localhost:3000`.

### Quick verification steps
1) Backend up
   - `make dev-db && make dev-migrate && make dev-api`
   - Check: `curl http://localhost:8000/readyz` → `{ "ok": true }`.
2) Chat transcript
   - POST `http://localhost:8000/api/mcp/chat/echo` with body `{ session_id, user_message }` and header `Authorization: Bearer dev-token`.
   - Expect 200; row(s) added in `semantic_memory` with `scope='chat'`.
3) Frosty telemetry
   - POST `http://localhost:8000/api/v1/frosty/suggest_v2` with minimal `text` and header.
   - Expect 200; row(s) added in `semantic_memory` with `scope='frosty'`.
4) Uploads → semantic memory
   - POST `http://localhost:8000/api/v1/uploads/files` with form-data (files, `scope`, `metadata_json`).
   - Expect 201; row(s) added in `semantic_memory` with `scope='portfolio'` (or chosen scope).
5) Blueprints CRUD
   - POST `http://localhost:8000/api/v1/blueprints/` with a minimal valid blueprint + auth header.
   - Expect 201; row appears in `blueprints`.

### Frontend expectations (now)
- UI should load and be able to call API at `http://localhost:8000`.
- Canvas renders; basic interactions are available. Full end-to-end compile/run from UI may be limited until we wire more pages to the new API routes.

### Exercises / demos
- “Chat agent transcript” demo: call `/api/mcp/chat/echo` 2–3 times and verify `semantic_memory` growth.
- “Upload and search” demo: upload two text files, confirm rows in `semantic_memory`; test filtered search via internal tools or bespoke endpoint.
- “Frosty suggest” demo: call suggest_v2 and verify `frosty` rows.
- “Blueprint create” demo: create a simple blueprint and verify DB row.

### Troubleshooting
- API not ready: `docker compose -f config/deploy/docker-compose.prod.yml logs --tail=200 api`.
- DB schema missing: ensure `make dev-migrate` ran (uses sync DSN with `sslmode=disable`).
- Auth: use `Authorization: Bearer dev-token` (allowed by `ICE_ALLOW_DEV_TOKEN=1`).
- Redis: ensure service is up and reachable; `/readyz` will report redis reachability.

### Notes
- Migrations are never run in-app. Always use `make dev-migrate`.
- DB is SSOT; semantic_memory stores chat transcripts, uploads, and frosty telemetry.
- All DB sessions are context-managed; engines are disposed on shutdown to avoid GC warnings.
