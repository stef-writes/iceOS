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
