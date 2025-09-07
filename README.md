## Testing & CI (single source of truth)

- Canonical unit/lint/type: `make ci`
- Canonical dockerized integration suite: `make ci-integration`
- Do not run raw pytest/poetry for CI; Make targets rebuild images and set envs.

## Runtime guarantees

- LLM nodes require explicit `llm_config`; no implicit inference in conversion.
- Executions reject malformed blueprints with 422 (empty node ids/deps).
- DB session teardown is cancellation-safe; CancelledError/MemoryError during close is ignored.

# iceOS – Intelligent Orchestration Platform

## Runtime features (enforced extras)

- **WASM sandbox (wasmtime)**: `ICE_ENABLE_WASM=1` (default) to run code nodes in a sandbox. Disabled or missing wasmtime → runtime error.
- **LLM providers**: OpenAI (required), Anthropic, DeepSeek supported. API keys via `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`.
- Database/pgvector (production‑ready): Postgres with `pgvector` backs components, blueprints, executions/events, tokens, and semantic memory (vector search). Redis is used only for ephemeral caches.

See Dockerfile for enforced extras export.

## Production Deployment (Docker Compose)

Quick start with the full stack (API + Postgres/pgvector + Redis cache):

```bash
docker compose up --build
```

Environment variables are sourced from `config/dev.env.example` and can be overridden in the compose file. The API container sets `ICEOS_RUN_MIGRATIONS=1` and `ICEOS_REQUIRE_DB=1` so Alembic upgrades run and readiness requires a healthy DB and applied head. For Redis hardening and retention:

```env
REDIS_URL=rediss://user:pass@host:6379/0
REDIS_CLIENT_NAME=ice_api
REDIS_DECODE_RESPONSES=1
REDIS_SOCKET_TIMEOUT=5.0
REDIS_SOCKET_CONNECT_TIMEOUT=3.0
REDIS_MAX_CONNECTIONS=100
CHAT_TTL_SECONDS=2592000
EXECUTION_TTL_SECONDS=604800
```

## Local dev (compose)

See `docs/QUICKSTART.md` for the repeatable Docker Compose flow used in dev. It covers bringing up Postgres/Redis, running one-shot migrations, starting the API, and verifying `/readyz`.

### Staging (Supabase)

See `docs/STAGING.md` for running the API against Supabase (transaction pooler), smoke steps, and integration targets.

- Fast subset: memory tools (MCP), library CRUD, ask_my_library
- Full suite: `make ci-integration-staging DATABASE_URL=postgresql+asyncpg://...:6543/postgres`

### Studio/Canvas – AI Builder
### Production deployment

See `docs/DEPLOY_PROD.md` for compose/Kubernetes secrets injection and prod flags. A ready-to-use override is at `config/deploy/docker-compose.prod.yml`.

See `docs/STUDIO_CANVAS_BUILDER.md` for how to call the Builder MCP endpoints, surface Q/A and cost, save drafts/sessions, and safely preview generated code.

## Chat (note)

The public REST surface is focused on blueprints/executions/MCP. If you need a chat abstraction, prefer registering an agent/workflow and using the executions API. The `IceClient.chat_turn` helper is subject to change and may be removed if no server route is provided.

> *No-fluff, fully-typed, test-driven micro-framework for composable AI/LLM workflows in Python 3.11.9.*

---

## 1. What is iceOS?

iceOS is an **experimental DAG orchestrator** and supporting toolkit that lets you describe multi-step workflows – CSV ingestion → pricing → copywriting → HTTP POST – entirely in Python **or** YAML blueprints.  Nodes are executed asynchronously, inputs/outputs are validated with Pydantic, and every public-facing API is covered by strict typing & tests.

Think of it as the narrow slice of Airflow you actually need for LLM apps, minus heavyweight scheduling cruft – plus first-class support for:

* ✨ **LLM nodes** (OpenAI, Anthropic, DeepSeek)
* 🔄 **Loop / recursive** execution with automatic context propagation
* 🧰 **Toolkits** – pluggable bundles of ready-made tools (`csv_loader`, `pricing_strategy`, …)
* 📦 **Single-process dev mode** – run everything locally before you deploy anything
* 🏭 **Factory Pattern** – fresh instances for every execution, no singleton state

> Status: **Beta (0.5.0)** – APIs stabilizing. mypy strict, tests and lint pass; demos run end-to-end.

---

## Deterministic one‑shot run (verified)

Start an execution and return the final result in a single call using `wait_seconds`.

```bash
curl -sS -X POST "http://localhost:8000/api/v1/executions/?wait_seconds=10" \
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

WASM gate for code nodes:

```84:92:src/ice_orchestrator/execution/executors/builtin/code_node_executor.py
        # 4. Execute in WASM sandbox (gated by ICE_ENABLE_WASM) -----------
        import os as _os
        if execute_node_with_wasm is None or _os.getenv("ICE_ENABLE_WASM", "1") != "1":
            raise RuntimeError("WASM execution is unavailable; enable ICE_ENABLE_WASM=1 and install 'wasmtime'.")
```


## 2. Requirements

* Python **3.11.9** (pinned in Docker/CI)
* `make` & a modern C compiler (for `uvicorn`, `httpx` wheels)
* Optional: Docker (for sandboxing Kuyamux WASM tests)

---

## 3. Installation (editable dev mode)

```bash
# Clone
$ git clone https://github.com/your-org/iceOS.git
$ cd iceOS

# Create & activate virtualenv (any tool – here: venv)
$ python -m venv .venv
$ source .venv/bin/activate

# Install Python deps (Poetry 2.x)
$ pip install "poetry>=2.1"
$ poetry install --with dev --no-interaction

# Add src/ to editable path so examples can do `import ice_orchestrator`
$ pip install -e .
```

Environment variables (copy `.env.example` to `.env` or export manually):

```env
# Required only for live demos
OPENAI_API_KEY="sk-..."
ICE_TEST_MODE=1   # set to 0 for live network calls

# Database (Postgres + pgvector)
DATABASE_URL=postgresql+asyncpg://iceos:iceos@localhost:5432/iceos
# Run Alembic migrations and require DB readiness at startup (recommended for prod)
ICEOS_RUN_MIGRATIONS=1
ICEOS_REQUIRE_DB=1
```

---

## 4. Quick Start – run the Seller Assistant demo

```bash
# Offline, synthetic LLM responses (fast)
$ python plugins/bundles/chatkit/examples/tiny_docs.md  # See Bundles section below

# Same but declarative builder API
$ python examples/seller_assistant_direct.py

# Real OpenAI calls – requires OPENAI_API_KEY
$ export OPENAI_API_KEY="sk-..."
$ python examples/seller_assistant_live.py

# Create new factory-based components
$ ice new tool my_tool
$ ice new agent my_agent
$ ice new llm-operator my_llm
```

### 4.1 From zero to a running blueprint (authoring path)

```bash
# Create a minimal blueprint JSON
$ ice blueprints new --name hello_world

# Push to the API (requires token)
$ ICE_API_TOKEN=dev-token ice push Blueprint.min.json --api http://localhost:8000 --token $ICE_API_TOKEN
Blueprint ID: bp_...

# Run and stream status (polling)
$ ice run bp_... --api http://localhost:8000 --token $ICE_API_TOKEN --input text="hi"
```

#### Generate a new tool from the CLI

```bash
$ ice generate tool MyWriter --out-dir src/ice_tools/generated --description "Writes a short paragraph"
# Tools generated under src/ice_tools/generated are auto-registered when the package is imported.
```

### 4.2 Compile a Python DSL file into Blueprint JSON

```bash
$ cat > examples/dsl_demo.py <<'PY'
from ice_builder import WorkflowBuilder

def build():
    b = WorkflowBuilder("dsl_demo")
    b.add_tool("echo", tool_name="echo_tool", text="hello")
    return b.build()
PY

$ ice build examples/dsl_demo.py --output examples/dsl_demo.json
$ ICE_API_TOKEN=dev-token ice push examples/dsl_demo.json --api http://localhost:8000 --token $ICE_API_TOKEN
$ ice run <blueprint_id> --api http://localhost:8000 --token $ICE_API_TOKEN
```

#### Author-time preflight validation

```python
from ice_builder import WorkflowBuilder

b = WorkflowBuilder("preflight_demo")
b.add_tool("t1", tool_name="lookup_tool", query="renewable energy")
issues = b.validate_resolvable()
assert not issues, f"Found issues: {issues}"
```

### 4.3 Author a minimal YAML blueprint and build it

```yaml
# examples/minimal.yaml (for reference; prefer Bundles/Templates for end users)
schema_version: "1.2.0"
metadata:
  draft_name: minimal_yaml
nodes:
  - id: n1
    type: tool
    name: echo
    tool_name: echo_tool
    dependencies: []
```

```bash
$ ice build examples/minimal.yaml --output examples/minimal.json
$ ICE_API_TOKEN=dev-token ice push examples/minimal.json --api http://localhost:8000 --token $ICE_API_TOKEN
$ ice run <blueprint_id> --api http://localhost:8000 --token $ICE_API_TOKEN
```

Expected output (truncated):

```jsonc
{
  "total": 9,
  "success": 9,
  "failures": 0,
  "items": [
    { "listing_id": "LOC-refrigerator-...", "price": 750.0, ... },
    ... 8 more items ...
  ]
}
```

The live run additionally starts a local FastAPI *mock HTTP bin*; browse the stored payloads at the printed URL.

---

## 5. Running the Test-Suite + linters

```bash
# Unit + integration tests (with coverage gate)
$ make test

# Type-check (strict) & style
$ make type
$ make lint
```

### 5.0 CI / Dev Quickstart (Dockerized)

```bash
make lint-docker
make lock-check-docker
make type-check
make test
```

### 5.0.1 Integration tests (Docker Compose)

```bash
make ci-integration
```

### 5.0.2 Benchmarks (ChatKit)

```bash
# Start stack and ingest examples, then run benchmark
make demo-rag
make bench-chatkit Q="Summarize my resume"
```

Coverage gate: 60% total (temporary). Raise gradually.

### 5.1 Integration tests (Docker Compose)

Offline integration tests run entirely in Docker and do not require provider keys:

```bash
# Build fresh images and run the itest suite
docker build --no-cache --target api -t local/iceosv1a-api:dev .
docker build --no-cache --target test -t local/iceosv1a-itest:dev .
IMAGE_REPO=local IMAGE_TAG=dev \
  docker compose -f docker-compose.itest.yml up --abort-on-container-exit --exit-code-from itest
```

Notes:
- First‑party tools are loaded via plugin manifests set by `ICEOS_PLUGIN_MANIFESTS`.
- The unified registry is idempotent; loading the same manifest multiple times is safe.
- Containers export `PYTHONPATH=/app/src:/app` so imports like `plugins.*` resolve.
- Integration runner uses fixed pytest options: `-p no:xdist --timeout=300 -q`.
- Canonical API routes use trailing slashes for collections (e.g. `/api/v1/executions/`).
- Execution and blueprint endpoints return typed Pydantic models.
- RAG via HTTP: call `/api/mcp/` and include `Authorization: Bearer <token>`; optionally set `X-Org-Id`/`X-User-Id`.

Runner behavior:
- The itest container executes `scripts/itest_runner.sh`, which runs suites sequentially to reduce peak memory usage.
- Set `ICE_SKIP_STRESS=1` to skip heavy resource stress tests on constrained runners (default in CI).
- Toggle WASM path for code nodes via `ICE_ENABLE_WASM` (0/1). In CI we keep it off for integration, with an opt‑in WASM job on capable runners.

Example (local, with stress skipped):
```bash
ICE_SKIP_STRESS=1 \
IMAGE_REPO=local IMAGE_TAG=dev \
docker compose -f docker-compose.itest.yml up --abort-on-container-exit --exit-code-from itest
```

### 5.1.1 Echo LLM for offline tests
### 5.1.2 Postman collection

Import `config/postman/iceos.postman_collection.json` into Postman. Set collection variables:
- `baseUrl` (default `http://localhost:8000`)
- `apiToken` (default `dev-token`)

Then run: Health → Blueprints (Create) → Executions (Start/Status).


Tests should avoid real LLM calls. Register the echo LLM and prefer model `gpt-4o` in tests:

```python
from ice_core.unified_registry import register_llm_factory
register_llm_factory("gpt-4o", "scripts.ops.verify_runtime:create_echo_llm")
```

Then set up starter-pack tools in-test as needed:

```python
from pathlib import Path
from ice_core.unified_registry import registry
mp = Path(__file__).parents[3] / "plugins/kits/tools/memory/plugins.v0.yaml"
registry.load_plugins(str(mp), allow_dynamic=True)
```

---

## 5.2 CLI reference

All commands are subcommands of `ice`.

- `ice doctor {lint|type|test|all}`: Run repo health checks via Makefile.
- `ice new ...`: Scaffold components.
  - `ice new tool NAME [--description --output-dir --dry-run]`
  - `ice new agent NAME [--description --system-prompt --tools --output-dir]`
  - Other scaffolds: `agent-tool`, `llm-node-tool`, `workflow`, `llm`, `condition`, `loop`, `parallel`, `recursive`, `code`, `human`, `monitor`, `swarm`.
- `ice push FILE.json [--api URL --token TOKEN]`: Upload a blueprint JSON to the API; returns `blueprint_id` and caches it for `--last`.
- `ice run [BLUEPRINT_ID] [--last] [--input k=v ...] [--api URL --token TOKEN]`: Start execution and stream status (polling) until completion.
- `ice run-blueprint FILE.json [--remote URL --max-parallel N]`: Execute locally (default) or remotely (if `--remote`).
- `ice blueprints new [--name NAME --output FILE]`: Create a minimal valid blueprint JSON.
- `ice build SOURCE.py [--output FILE]`: Compile a Python DSL file with a `build()` function returning a Blueprint into JSON.
- `ice plugins ...`: Manage plugin manifests (advanced).
- `ice schemas export|import ...`: Export/import JSON Schemas for validation.

Each command focuses on a single responsibility to keep the UX predictable and composable.

---

## 5.3 End-to-end authoring flow (user journeys)

Below are the core stages a user goes through to build a robust system, with the corresponding commands and API endpoints.

1) Discover
   - Goal: understand available nodes/tools/agents/workflows and their schemas.
   - API:
     - `GET /api/v1/meta/nodes` – catalog (tools with schemas, agents, workflows, chains)
     - `GET /api/v1/meta/nodes/types` – canonical node types
     - `GET /api/v1/meta/nodes/{node_type}/schema` – Pydantic JSON Schema for config
     - `GET /api/v1/meta/nodes/tool/{tool_name}` – tool details and schemas
   - CLI: `ice blueprints new`, `ice build` (see examples above)

2) Draft (design-time)
   - Goal: create or open a collaborative draft and mutate it safely.
   - API (Builder):
     - `PUT /api/v1/builder/drafts/{key}` – create/update draft
     - `GET /api/v1/builder/drafts/{key}` – read draft
     - `DELETE /api/v1/builder/drafts/{key}` – delete draft (idempotent)
   - Sessions (preferences/history per user):
     - `PUT /api/v1/builder/sessions/{session_id}` – create/update session state
     - `GET /api/v1/builder/sessions/{session_id}` – read session state
     - `DELETE /api/v1/builder/sessions/{session_id}` – delete session state

3) Validate/Compile (MCP compiler tier)
   - Goal: convert partial blueprints into validated, frozen specs; catch errors early.
   - API (MCP JSON-RPC preferred): `POST /api/v1/mcp`
     - methods: `initialize`, `components/validate`, `prompts/*`, `tools/*`, `network.execute`
   - API (Legacy MCP REST): `POST /api/mcp/components/validate` (deprecated path maintained for tests)
   - CLI: `ice build` (from DSL/YAML), `ice push` (upload JSON)

4) Execute (runtime)
   - Goal: start execution, observe live progress, and retrieve results.
   - API:
     - `POST /api/v1/executions` – start → `execution_id`
     - `GET /api/v1/executions/{id}` – status/result
     - `GET /api/v1/executions` – list
     - `POST /api/v1/executions/{id}/cancel` – cancel
     - WS: `ws://.../ws/executions/{id}` – live status (optional; CLI uses polling by default)
   - CLI: `ice run <blueprint_id> [--input k=v]`

5) Govern/Optimize
   - Goal: enforce budget, get actionable suggestions and explanations.
   - API:
     - Budget preflight on `POST /api/v1/executions` (402 with details when over-limit)
     - MCP suggestions: `.../blueprints/partial/{id}/suggest`, and node/graph analysis endpoints under MCP API

6) Iterate
   - Goal: apply changes safely with optimistic locks and re-run.
   - API: blueprint CRUD with `X-Version-Lock` or `If-Match` (coming), drafts mutations.
   - CLI: `ice push` (overwrites with lock), `ice run --last`.

This flow keeps responsibilities clear (discover → draft → validate → execute → observe → iterate) and maps 1:1 to the CLI and API surfaces implemented in this repo.

---

## 5.2 Backend MVP status (Agentic Studio – server-side)

The backend is production-grade for a no/low-code Agentic Studio MVP:

- Blueprint lifecycle
  - Redis-backed CRUD with optimistic locking and version headers
  - Partial blueprints: create/get/update (with `X-Version-Lock`) and finalize
  - Stateless suggest endpoint: read-only by default; `commit=true` requires lock

- Executions
  - Start/status/list/cancel endpoints; state persisted in Redis
  - Per-node/workflow events collected in execution snapshots and streamed via WS

- Governance
  - Deterministic budget preflight: blocks over-budget runs with a non-zero floor for allowed LLM models (no GPT‑3.5)
  - Compile-time schema validation prior to finalize/execute

- Quality gates
  - mypy `--strict`: clean; ruff/isort: clean; tests: green

Key endpoints

- `POST /api/v1/blueprints/` (X-Version-Lock: __new__) → id + lock
- `GET /api/v1/blueprints/{id}` → body + X-Version-Lock
- `PATCH|PUT|DELETE /api/v1/blueprints/{id}` (optimistic locking)
- `POST /api/mcp/blueprints/partial` → partial blueprint id
- `GET /api/mcp/blueprints/partial/{id}` → body + X-Version-Lock
- `PUT /api/mcp/blueprints/partial/{id}` (requires X-Version-Lock)
- `POST /api/mcp/blueprints/partial/{id}/finalize` (requires X-Version-Lock)
- `POST /api/mcp/blueprints/partial/{id}/suggest` (read-only; `commit=true` requires X-Version-Lock)
- `POST /api/v1/executions/` → execution_id
- `GET /api/v1/executions/{execution_id}`
- `GET /api/v1/executions` (list)
- `POST /api/v1/executions/{execution_id}/cancel`

Notes

- Rate limiting is disabled under tests to avoid flakiness; enabled in dev/prod
- Budget preflight blocks with 402 when estimated avg cost exceeds `ORG_BUDGET_USD`
- Allowed models exclude legacy GPT‑3.5 family; use `gpt-4o`/`gpt-4-turbo-*` etc.

---

## 6. Package overview

| Package | What lives here |
|---------|-----------------|
| `ice_core` | Pure-Python domain models, validation, metrics, registry & core tool abstractions |
| `ice_orchestrator` | DAG execution engine, node executors, retry logic |
| `ice_builder` | Authoring DSL + fluent `WorkflowBuilder` helper |
| `ice_cli` | `ice` command-line utility (`ice scaffold`, `ice run`, …) |
| `ice_client` | Thin HTTP client in `src/ice_client` |

Docs for each live in the corresponding `README.md` files.

---

## 7. Architecture layers (design → compile → run)

| Phase | Tier | Responsibility | Code/Service |
|-------|------|----------------|--------------|
| Design-time | Canvas UI (future) | Human sketches workflow via spatial + NL interface | *Frontend repo* (yet to be open-sourced) |
| Compile-time | MCP API / Validator | Convert partial blueprints into **frozen, validated** JSON specs; static checks, ID uniqueness, schema validation | `ice_api` (MCP), `ice_builder`, schemas/ |
| Run-time | DAG Engine | Execute the compiled blueprint asynchronously; retries, context propagation, metrics | `ice_orchestrator` + workers |

Data flows strictly **left → right**; each layer depends only on the one below it (`interface → orchestrator → core`).  This yields:

* Early failure – compile-time catches errors before any costly LLM calls.
* Horizontal scalability – run-time workers scale independently.
* Stable contract – only the JSON Blueprint schema is shared across tiers.

---

## 8. Developing new tools

1. **Subclass** `ice_core.base_tool.ToolBase`.
2. Implement `_execute_impl(**kwargs) → dict` (async).
3. Add Pydantic **config fields** for static parameters.
4. Optionally override `get_input_schema` / `get_output_schema`.
5. Register a factory once:
   ```python
   from ice_core.unified_registry import register_tool_factory
   register_tool_factory(tool.name, "your_module_path:create_my_tool")
   ```

External side-effects *must* stay inside `_execute_impl`.

---

## 9. Contributing

* Fork → feature branch → PR – follow **mypy strict** & **ruff**.
* Each new node/tool requires tests ≥ 90 % coverage.
* No `# type: ignore` in core layers.
* No marketing language in docs – facts only.

Full guidelines in [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 10. License

`Apache-2.0`.  See [`LICENSE`](LICENSE).
