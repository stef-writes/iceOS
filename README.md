# iceOS v1
[![CI](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml/badge.svg)](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml)

The open-source **Intelligent Composable Environment** for building agentic workflows on top of your data, services, and events.

iceOS bundles a pluggable SDK (`ice_sdk`) and a reference application (`app`) so you can compose Tools, Nodes, EventSources, and Chains that talk to modern LLMs or any REST / RPC backend.

## Component map (one screen)

| Layer / Dir | Purpose |
| ----------- | ------- |
| `src/ice_sdk/` | Core abstractions (`BaseNode`, `BaseTool`) and runtime helpers. |
| `src/app/agents/` | Opinionated Agent implementations ready to orchestrate Chains. |
| `src/app/chains/` | Re-usable multi-step Chains (scripted or declarative). |
| `src/app/nodes/` | Domain-specific Nodes extending `BaseNode`. |
| `src/app/tools/` | Side-effecting Tools: DB access, HTTP calls, file I/O, etc. |
| `src/app/event_sources/` | Webhooks, schedulers, and other external triggers. |
| `src/app/services/` | Pure-Python services (e.g. vector indexes, caching). |
| `src/schemas/` | Pydantic models shared across the stack. |
| `docs/` | User-facing guides & ADRs. |
| `tests/` | Pytest suites and health checks. |

> For a per-package bird's-eye view see `docs/codebase_overview.md`.

---

### Get started

```bash
# create virtual env
python -m venv .venv && source .venv/bin/activate

# install core deps
pip install -r requirements.txt

# run reference app
python src/app/main.py
```

### Refresh generated docs

```bash
make refresh-docs
```

---

© 2025 iceOS contributors – MIT License 