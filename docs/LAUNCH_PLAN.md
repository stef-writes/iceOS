## Launch Plan: Data & Migrations

### Postgres / pgvector versions
- Use `ankane/pgvector:0.5.1-pg15` (Postgres 15 + pgvector 0.5.1) in Compose.
- For managed Postgres, install `pgvector` extension at the same version.

### Migrations on cold start
- Env flags:
  - `ICEOS_RUN_MIGRATIONS=1` (run Alembic upgrade to head at boot)
  - `ICEOS_REQUIRE_DB=1` (fail startup if DB not reachable)
  - `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`
- The app will:
  - Convert DSN to psycopg2 for Alembic
  - Run `ensure_version` and `upgrade head`
  - Verify schema exists (`semantic_memory` table)
  - Fallback to offline SQL if needed

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
