# iceOS – AI Agent & Workflow Orchestration Platform

[![CI](https://img.shields.io/github/actions/workflow/status/iceos-ai/iceOS/ci.yml?label=CI&logo=github)](https://github.com/iceos-ai/iceOS/actions)
[![Coverage](https://img.shields.io/codecov/c/github/iceos-ai/iceOS?logo=codecov)](https://codecov.io/gh/iceos-ai/iceOS)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs%20latest-blue)](https://iceos.ai/docs)

> **iceOS** is an open-source, plugin-driven operating system for building, testing and shipping AI-native applications – from single-shot tools to multi-agent reasoning chains.

## ✨ Key Features

* **Composable Workflows** – build agent graphs with Python, YAML _or_ the CLI wizard.
* **Strict Typing** – every node/tool uses Pydantic models; `mypy --strict` enforced by CI.
* **Async-First Runtime** – non-blocking execution with automatic context propagation.
* **Observability Out-of-the-box** – spans & metrics for every node/tool invocation.
* **Pluggable Providers** – swap LLMs (OpenAI, Anthropic, Gemini…), vector DBs (Chroma, Annoy …) or custom tools at runtime.
* **Frosty Meta-Layer** – optional UX/CLI wrapper that converts natural-language goals into ScriptChains and delegates execution to iceOS.
* **First-Class Tooling** – CLI, REST + WebSocket API, SDK, and rich test harness.

## 📦 Quick Start (Users)

```bash
# Clone & install (Python 3.10+)
git clone https://github.com/iceos-ai/iceOS.git && cd iceOS
poetry install --no-interaction --with dev

# Run the API server (localhost:8000)
poetry run uvicorn ice_api.main:app --reload --host 0.0.0.0 --port 8000

# Execute a sample chain via CLI
echo '"Hello AI"' | poetry run ice run examples/create_reasoning_chain.py --json
```

The interactive API docs are now live at `http://localhost:8000/docs` (FastAPI Swagger UI).

---

## 🛠️  Developer Guide

### 1. Project Setup

```bash
# Install dev dependencies and Git hooks
make install          # == poetry install --with dev
pre-commit install    # Lint/type/test hooks before every commit
```

Environment variables (API keys, etc.) live in `.env.local` (ignored) – copy `.env.example` to get started.

### 2. Essential Commands

| Task                  | Command                              |
|-----------------------|--------------------------------------|
| Lint & format         | `make lint`  /  `make format`        |
| Static typing         | `make type` (mypy --strict)          |
| Unit / integration CI | `make test`                          |
| Mutation testing      | `make mutation`                      |
| Build docs            | `make docs` → `site/`                |
| Full quality gate     | `make doctor`                        |

> All quality targets mirror what runs in GitHub Actions; a green local `make doctor` == green CI.

### 3. Directory Layout (TL;DR)

```text
src/
  ice_sdk/          # Core SDK – nodes, tools, providers, context store
  ice_orchestrator/ # Execution engine (DAG -> async graph runtime)
  ice_api/          # FastAPI server exposing REST & WS Gateway
  ice_cli/          # Typer-powered developer CLI
schemas/            # JSON Schema contracts (runtime & configuration)
docs/               # MkDocs site (architecture, guides, API spec)
```

A full breakdown is available in [docs/architecture/repo_layout.md](docs/architecture/repo_layout.md).

### 4. Running Tests

```bash
# Run all tests with coverage
make test
# or just a subset
pytest tests/unit/agents -q
```

Tests use **pytest** with fixtures in `tests/conftest.py`. Coverage ≥ 90 % on new lines is enforced by CI.

### 5. Coding Standards

1. **Type hints everywhere** – unchecked code is a bug magnet.
2. **No cross-layer imports** – enforced by `scripts/check_layers.py`.
3. **External side-effects only inside Tool implementations**.
4. **Raise domain-specific exceptions**; catch narrow subclasses.
5. All public APIs need Google-style docstrings **+** a minimal example.

See the full rule-set in [rules section](#) or `repo_specific_rule` in `.github/*`.

### 6. Contribution Workflow

1. Fork → feature branch (`feat/xyz`)
2. Commit messages: _<type>(scope): summary_ (Conventional Commits)
3. `make doctor` locally – must pass lint/type/test
4. Open PR; GH Actions will run the same suite + security scans
5. Once merged, the docs site auto-deploys via MkDocs Material.

---

## 🌐  Documentation & Community

* **User / Architecture Docs:** https://iceos.ai/docs
* **API Spec:** `docs/api/mcp.yaml` (OpenAPI 3)
* **Discussions & Support:** GitHub Discussions / Discord (*invite link TBD*)

Found a bug or have a feature request? Open an issue or start a discussion – contributions welcome! 🤗

## 📄 License

iceOS is released under the [MIT License](LICENSE).

> © 2024 iceOS Contributors – Made with 💙 and **async / await**. 