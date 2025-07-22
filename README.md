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

## 🚀 Zero to Demo in 60 Seconds

### First-time setup (⏱ ~30 s)

```bash
# 1 · create & activate local venv
python3 -m venv .venv && source .venv/bin/activate

# 2 · install the project in editable-dev mode
pip install -e ".[dev]"

# 3 · optional – run tests to confirm all good
pytest -q
```

### Daily workflow

```bash
# Terminal 1 – start services (hot-reload API + Redis)
make dev

# Terminal 2 – run the CSV→summary demo
make run-demo
```

Poetry will now reuse the `.venv` you created (see `poetry.toml`).

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
| **Node**       | Atomic unit – one of *tool*, *llm*, *agent*, *condition*, *nested_chain* |
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