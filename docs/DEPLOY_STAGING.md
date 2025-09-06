Staging runbook (Supabase + Docker)

Prerequisites
- DATABASE_URL: Supabase DSN (asyncpg), e.g. postgresql+asyncpg://user:pass@aws-0-us-east-2.pooler.supabase.com:6543/postgres
- CORS_ORIGINS: set to your staging frontend origin(s), e.g. https://studio.example.com
- TRUSTED_HOSTS: comma-separated list of hostnames the API will serve
- ICEOS_REHYDRATE_COMPONENTS=1: re-register components from repo on startup

Steps
1) Run migrations against Supabase
```bash
export DATABASE_URL=...  # asyncpg DSN
make supabase-migrate
```
2) Apply RLS policies (optional)
```bash
export PGHOST=... PGUSER=... PGPASSWORD=... PGDATABASE=...
make supabase-rls-apply
```
3) Build and run integration tests against staging DB
```bash
export DATABASE_URL=...
make ci-integration-staging
```
4) Configure API server env
```bash
export CORS_ORIGINS="https://studio.example.com"
export TRUSTED_HOSTS="api.example.com"
export ICEOS_REHYDRATE_COMPONENTS=1
```
5) Start API (docker-compose)
```bash
docker compose -f docker-compose.staging.yml up -d --remove-orphans
```

Frontend (local or hosted)
- NEXT_PUBLIC_API_URL: https://api.example.com
- NEXT_PUBLIC_API_TOKEN: staging token issued by the API (or dev-token if configured)

Live verification (optional)
```bash
export OPENAI_API_KEY=... # and others as needed
make ci-live
```

Notes
- CORS wildcard is disabled by default; for local dev set CORS_ORIGINS=* and ALLOW_CORS_WILDCARD=1.
- SSE uses sse_starlette if installed; falls back to text/event-stream. Frontend handles both.
