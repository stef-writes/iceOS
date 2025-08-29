## Launch Plan (No‑Code Hosted)

This plan reflects a no‑code product where end users interact solely via the hosted Studio Lite. Operator guidance is provided as an Appendix; end users do not need any CLI, SDK, or keys.

### Day‑1 Product Surface
- Hosted Studio Lite (no installation for end users)
- Auth: magic‑link email
- Pages: Library (upload/list), RAG Chat (bundle run), Components (discovery), Runs (history)
- Provider keys stored on API only; frontend calls public REST

### Acceptance Criteria
- New user can: upload → ask Library → get answer/citations → view run
- No API keys in the browser; all server‑side
- CORS/trusted hosts configured for the hosted domain

### Operational Readiness (API)
- Auth: Bearer tokens (issued by platform)
- CORS/trusted hosts explicitly set per environment
- Rate limiting enabled
- Readiness/liveness endpoints wired

### Supabase Staging Verification
- Staging override via `docker-compose.staging.yml` (pooler DSN, timeouts/retries defaults)
- Smoke green: MCP memory write/search, Library CRUD, Ask‑My‑Library
- Integration parity:
  - Fast subset against running API
  - Full suite optional: `make ci-integration-staging DATABASE_URL=postgresql+asyncpg://...:6543/postgres`

---

## Appendix: Data & Migrations (Operators)

### Postgres / pgvector versions
- Use `pgvector/pgvector:pg15` (Postgres 15 + bundled pgvector) in Compose.
- For managed Postgres, install the `pgvector` extension at a compatible version.

### Migrations on cold start
- Deployment pattern (recommended): run migrations as a one-shot job, separate from the API.
  - Compose: `docker compose run --rm migrate`
  - Production API should set `ICEOS_RUN_MIGRATIONS=0` (migrations disabled in API container)
- Env flags:
  - `ICEOS_REQUIRE_DB=1` (fail startup if DB not reachable)
  - `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`
- Migration workflow performs:
  - DSN conversion for Alembic
  - `upgrade head`
  - Schema verification (e.g., `semantic_memory` present)
  - Index verification: ensure composite indexes exist for Library performance
    - `(org_id, user_id, key)` and `(scope, org_id, created_at DESC)` on `semantic_memory`

### Sandbox overrides (resource limits)
- Defaults:
  - Timeout: 30s (asyncio cancel)
  - Memory: 512 MB (RLIMIT_AS)
  - CPU: 10 seconds (RLIMIT_CPU)
- Overrides via env (set in API container):
  - Not currently env-driven; adjust in `ResourceSandbox` constructor at call sites if stricter limits needed.
- CI/staging knobs:
  - `ICE_DISABLE_SECCOMP=1` (disable seccomp syscall filter; only for tests)
  - `ICE_SKIP_STRESS=1` (skip heavy stress tests; only for CI)

### API health and readiness
- Endpoints:
  - `/readyz` (readiness), `/livez` (liveness), `/healthz` (alias)
- MCP JSON-RPC mounted at `/api/v1/mcp/` (note trailing slash)

### Security hardening (app layer)
- Bearer token auth; dev token disabled by default:
  - `ICE_ALLOW_DEV_TOKEN=0` in production (set to `1` only in dev/tests)
- CORS and trusted hosts (required per environment):
  - `CORS_ORIGINS` and `ALLOW_CORS_WILDCARD=0` (set `ALLOW_CORS_WILDCARD=1` only in dev)
  - `TRUSTED_HOSTS` (comma-separated host patterns)
- Rate limiting (tune per environment):
  - `ICE_RATE_WINDOW_SECONDS`, `ICE_RATE_MAX_REQUESTS`

### Runtime connections (CI/test tuning)
- Redis max connections and background loop knobs for constrained CI:
  - `REDIS_MAX_CONNECTIONS=20`
  - `DISABLE_REDIS_BG_LOOP=1`

### Backup / Restore
- Backups (daily):
  - `pg_dump -Fc -d "$DATABASE_URL_PG" -f /backups/iceos_$(date +%F).dump`
  - Where `$DATABASE_URL_PG` is the psycopg2 DSN (postgresql://)
- Restore DR drill:
  - Provision a new Postgres instance
  - `createdb iceos`
  - `pg_restore -d "$DATABASE_URL_PG" /backups/iceOS_YYYY-MM-DD.dump`
  - Start API with `ICEOS_RUN_MIGRATIONS=1` and validate `/readyz` healthy
  - Run integration smoke: `make ci-integration`
- Compose quick backup/restore:
  - Backup: `docker exec -t iceos-postgres-1 pg_dump -U ${POSTGRES_USER:-iceos} ${POSTGRES_DB:-iceos} > backup_$(date +%F).sql`
  - Restore: `cat backup_YYYY-MM-DD.sql | docker exec -i iceos-postgres-1 psql -U ${POSTGRES_USER:-iceos} -d ${POSTGRES_DB:-iceos}`

### Operational Checks
- Confirm Alembic `head` recorded (`alembic_version` row present)
- Confirm `semantic_memory` table exists and accepts writes
- Monitor startup logs for `Alembic applied_head=`

### Edge Security (reverse proxy)
- Recommended nginx/ingress directives:
  - `add_header X-Frame-Options "DENY" always;`
  - `add_header X-Content-Type-Options "nosniff" always;`
  - `add_header Referrer-Policy "same-origin" always;`
  - `client_max_body_size 25m;` (tune uploads)

## Launch Plan – Step 1 (MVP)

### What must be finished to launch

- Product surface
  - Publish Python client to PyPI (`iceos-client`) with typed docs and quickstart.
  - Lock API routes and auth (Bearer token). Enable OpenAPI docs and export a Postman collection.
  - Ship one container: `iceos-api`; document env (Redis URL, API token, plugin manifests, provider keys).

- Persistence and multi-tenant basics
  - Persist blueprints, components, and run records (Postgres or durable KV). Include migrations and backup guidance.
  - Token issuance/validation (org/project/user) and simple RBAC (read/write on components/runs).

- DX and examples
  - Notebooks: SaaS quickstart + self-host quickstart.
  - CLI: scaffold → push → run flows; templates for custom tools; 2–3 end-to-end examples.

- Ops and security
  - CI gates: type-check, tests, wasm opt-in job, Trivy CVE clean, signed images.
  - Deploy docs: Docker Compose and Helm (prod-ready), secrets via env/manager.
  - Observability: structured logs, metrics, readiness/liveness, minimal tracing.
  - Policies: rate limiting, CORS, error budgets; provider key management.

- NL builder scope for MVP
  - Keep NL generation behind a feature flag; expose preview-only endpoints if not fully live.
  - Roadmap “write/test/validate custom tools” as Phase 2 (codegen + sandbox tests).

### Likely missing now

- PyPI packaging (client/CLI), versioning, release workflow.
- Persistent store for blueprints/runs (currently in-memory/Redis).
- Token management beyond `dev-token` and basic RBAC.
- Public docs site for SDK/CLI and API reference.
- A couple of polished first-party tools/demos that show value.

### Day-1 usefulness

- pip install the client, submit/monitor runs, deterministic results without keys.
- scaffold a tool, push it, run a workflow quickly.
- The DSL + registry + orchestrator are already valuable; NL builder can be additive later.

### Minimal launch cut

- Ship `iceos-api` + Redis.
- Publish `iceos-client` to PyPI; optional `ice` CLI.
- Lock auth, persistence, and docs.
- Include 2–3 cookbook notebooks and one “custom tool” tutorial.

---

## Feature Toggles (env-first)

Name | Default | Env | Notes
--- | --- | --- | ---
WASM | off | `ICE_ENABLE_WASM=1` | Falls back to non-WASM execution if unsupported
Stress (heavy tests) | off | `ICE_SKIP_STRESS=0` (and `ICE_DISABLE_SECCOMP=0`) | Run in nightly; validate stability
Metrics | off | `ICEOS_ENABLE_METRICS=1` | Requires `prometheus_client`; safe no-op when off
Drafts | off | `ICEOS_ENABLE_DRAFTS=1` | Authoring utility; not runtime-essential
CORS / Trusted Hosts | required | `CORS_ORIGINS`, `ALLOW_CORS_WILDCARD=0`, `TRUSTED_HOSTS` | Must be set per environment
Dev Token | off | `ICE_ALLOW_DEV_TOKEN=1` | Enable only in dev/tests
Rate Limiting | on | `ICE_RATE_WINDOW_SECONDS`, `ICE_RATE_MAX_REQUESTS` | Tune per environment

## Feature Matrix

- Foundational: Sandboxing / Resource limits (always on)
- Platform: WASM (included; enable per environment)
- Optional: Metrics, Drafts (off by default; flip when needed)
- Required Configuration: CORS_ORIGINS / TRUSTED_HOSTS (environment-specific)

## Promote-to-required (WASM/Stress)

- Run optional lanes nightly for N days (e.g., 7–14)
- Track flake rate ≤ agreed threshold (e.g., 0–1 intermittent failures)
- If green:
  - Flip WASM lane to required in PR workflow
  - Keep Stress required in nightly first, then evaluate in PR after additional soak

## RAG Conversational Demo (multi-turn)
## Bundles and Kits (distribution)

- Bundle is the deployable unit. A Bundle can contain one or more workflows and presets.
- Kits provide reusable Tools (capabilities); Connectors are Kits integrating third-party systems.
- Example:
  - Kits: `plugins/kits/tools/memory`, `plugins/kits/tools/search`
  - Bundle: `plugins/bundles/chatkit` with `bundle.yaml` (entry `chatkit.rag_chat`)
  - Build: `ice bundle build plugins/bundles/chatkit` → `dist/bundles/chatkit-1.0.0.ice.tgz`
  - Run: `ice bundle run chatkit --file ... --note ... --query ... --session s1`


Prerequisites:
- `OPENAI_API_KEY` set (LLM provider defaults to OpenAI when available)
- Compose environment up for DB/Redis and API

One-command demo (ingest + query):

```bash
make demo-rag Q="Give me a two-sentence professional summary for Stefano."
```

Manual sequence:

```bash
docker compose up -d postgres redis
docker compose run --rm migrate
docker compose up -d api
make demo-wait
# Ingest example assets and run a query (inside the API container via helper script)
python - <<'PY'
import json, httpx
BASE="http://localhost:8000"; token="dev-token"
with httpx.Client() as c:
    c.post(f"{BASE}/api/v1/mcp/", json={"jsonrpc":"2.0","id":0,"method":"initialize","params":{}} , headers={"Authorization": f"Bearer {token}"}).raise_for_status()
    for fn in ("resume.txt","cover_letter.txt","website.txt"):
        text=open(f"examples/user_assets/{fn}","r",encoding="utf-8").read()
        payload={"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"tool:memory_write_tool","arguments":{"inputs":{"key":fn,"content":text,"scope":"kb"}}}}
        c.post(f"{BASE}/api/v1/mcp/", json=payload, headers={"Authorization": f"Bearer {token}"}).raise_for_status()
    payload={"blueprint_id":"chatkit.rag_chat","inputs":{"query":"Give me a two-sentence professional summary for Stefano.","org_id":"demo_org","user_id":"demo_user","session_id":"chat1"}}
    r=c.post(f"{BASE}/api/v1/executions/", json=payload, headers={"Authorization": f"Bearer {token}"}); r.raise_for_status(); exec_id=r.json()["execution_id"]
    print(c.get(f"{BASE}/api/v1/executions/{exec_id}", headers={"Authorization": f"Bearer {token}"}).json())
PY
```

Notes:
- Multi-turn memory is enabled via `recent_session_tool` + `memory_write_tool` using `session_id`.
- The MCP router is mounted at `/api/v1/mcp/`; the demo script initializes MCP before `tools/call`.
- Images are tagged with the Git SHA during publish for traceability.
