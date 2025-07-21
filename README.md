# iceOS

> *“Give every distributed team a shared canvas where natural-language ideas become governance-ready AI workflows in seconds.”*

---

## What is iceOS?

iceOS is an **alpha-stage AI workflow runtime** designed for:

* **Zero-code design** – blueprints created from natural language via Frosty or the canvas editor
* **Governed execution** – budget & safety guardrails enforced at runtime
* **Team memory** – every run is traceable, costed and searchable

The runtime is powered by a deterministic DAG engine (**Workflow**) and exposed through the **Model Context Protocol (MCP)** HTTP API.

---

## Quick Start

### 1 · Prerequisites

* Python 3.11+
* Redis ≥6 (for blueprint + event persistence)
* Poetry (`pip install poetry`)

### 2 · Clone & install

```bash
poetry install --with dev
```

### 3 · Start the API

```bash
export REDIS_URL="redis://localhost:6379/0"  # adjust as needed
poetry run uvicorn ice_api.main:app --reload
```

### 4 · Run a workflow

```bash
# sum_blueprint.json
{
  "blueprint_id": "hello-sum",
  "nodes": [
    {"id": "sum1", "type": "tool", "tool_name": "sum", "tool_args": {"a": 2, "b": 3}}
  ]
}

# Register blueprint
curl -X POST http://localhost:8000/api/v1/mcp/blueprints \
     -H "Content-Type: application/json" \
     -d @sum_blueprint.json

# Execute blueprint
RUN_ID=$(curl -s -X POST http://localhost:8000/api/v1/mcp/runs \
  -H "Content-Type: application/json" \
  -d '{"blueprint_id":"hello-sum"}' | jq -r .run_id)

# Stream node-level events (requires curl ≥7.72)
curl --no-buffer http://localhost:8000/api/v1/mcp/runs/$RUN_ID/events

# Fetch final result
curl http://localhost:8000/api/v1/mcp/runs/$RUN_ID | jq
```

---

## Repository Layout

```
src/
  ice_core/          # shared models, contracts, utilities
  ice_sdk/           # design-time SDK & client helpers
  ice_orchestrator/  # runtime execution engine
  ice_api/           # FastAPI HTTP façade
examples/            # runnable samples
```

More details in [docs/architecture/repo_layout.md](docs/architecture/repo_layout.md).

---

## Key Concepts

| Term           | Description |
|----------------|-------------|
| **Blueprint**  | Design-time JSON object defining nodes and edges |
| **Workflow**   | In-memory runtime representation of a blueprint |
| **Node**       | Atomic unit – either *tool*, *ai* (LLM operator) or *condition* |
| **MCP**        | HTTP protocol for creating blueprints, starting runs and tailing events |
| **Event Stream** | Redis Stream `stream:{run_id}` emitting `workflow.nodeStarted`, `workflow.nodeFinished`, `workflow.finished` |

---

## Roadmap (H2 2025)

| Milestone | ETA | Highlights |
|-----------|-----|-----------|
| **B0 – Alpha Solo** | Aug 2025 | Natural-language → Blueprint parser; local canvas prototype |
| **B1 – Private Beta Teams** | Nov 2025 | Real-time **Canvas** collaboration; live cost overlay |
| **B2 – Public Beta** | Feb 2026 | One-click deploy; **Frosty** optimisation loop |
| **B3 – Marketplace** | Jun 2026 | Paid third-party tools; revenue share |

> The current repository implements the **B0 runtime spine** (MCP API + Redis persistence). The canvas editor and Frosty meta-agents live in separate repos and will be merged once stabilised.

---

## Development

Run the full suite (type-check, lint, tests, coverage):

```bash
make test
```

Strict mypy config is enforced (`mypy --strict`). Test coverage on changed lines must be ≥ 90 %.

---

## Contributing

1. Fork and create a feature branch.
2. Follow repository rules (see `.github/CONTRIBUTING.md`).
3. Ensure **CI is green** (`make test`) before opening PR.

---

## License

[Apache-2.0](LICENSE) 