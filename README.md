# iceOS v1 – Intelligent Composable Environment

[![CI](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml/badge.svg)](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml)

> **iceOS** is an *open-source* operating layer for building **agentic, event-driven AI applications** on top of your data, services, and infrastructure.
>
> It provides a principled architecture, ready-to-use primitives, and ergonomic developer tooling so that you can ship production-grade AI features in **minutes—not months**.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Strategic Vision & Moats](#strategic-vision--moats)
3. [Conceptual Overview](#conceptual-overview)
4. [Architecture](#architecture)
5. [Repository Layout](#repository-layout)
6. [Quick Start](#quick-start)
7. [Configuration](#configuration)
8. [Working With iceOS](#working-with-iceos)
   1. [Creating a Node](#creating-a-node)
   2. [Creating a Tool](#creating-a-tool)
   3. [Building a Chain / Agent](#building-a-chain--agent)
9. [Testing & Quality](#testing--quality)
10. [Roadmap](#roadmap)
11. [Contributing](#contributing)
12. [License](#license)
13. [Deprecation Notices](#deprecation-notices)
14. [Common Tasks](#common-tasks)

---

## Strategic Vision & Moats

The **long-term game plan** for iceOS—including differentiators, open-source moats, and multi-phase roadmap—lives in **[`docs/vision_and_moats.md`](docs/vision_and_moats.md)**.

If you want to understand *why* we are building certain features (and in which order), start there.

---

## Key Features

🚀 **Ready-to-run skeleton** – A batteries-included reference app demonstrates best practices and lets you prototype immediately.

🧩 **Composable primitives** – Nodes, Tools, Chains, and Agents snap together like Lego® bricks so you can express complex workflows declaratively.

⛓️ **Asynchronous & non-blocking** – The entire runtime is **async-first**. Long-running I/O never blocks the event-loop, enabling massive horizontal scalability.

🔒 **Type-safe by design** – Extensive type-hints and Pydantic models catch bugs at *import-time* instead of *runtime*.

📡 **Event-driven** – A unified event spec (`source.eventVerb`) lets disparate systems publish and subscribe in a predictable manner.

🧑‍💻 **Layered architecture** – Clean separation of concerns keeps business logic, side-effects, and infrastructure code isolated.

---

## Conceptual Overview

| Primitive | Responsibility | Lives in | Notes |
|-----------|----------------|---------|-------|
| **Node**  | *Pure* business/domain logic. | `app/nodes/` | No side-effects. Stateless. |
| **Tool**  | External side-effects (DB, HTTP, LLM). | `app/tools/` | All I/O encapsulated here. |
| **Chain** | Multi-step deterministic workflow. | `app/chains/` | Describes *how* to orchestrate Nodes & Tools. |
| **Agent** | Goal-directed autonomous worker. | `app/agents/` | Owns state & decision-making. |
| **Event Source** | Emits events that trigger workflows. | `app/event_sources/` | e.g. Webhook, scheduler. |

If you know *LangChain*, think **Node = Runnable**, **Tool = Tool**, **Chain = Chain**, **Agent = Agent**—but with stricter typing & clearer boundaries.

---

## Architecture

```
┌───────────────────────────────┐
│            Clients            │
└──────────────▲────────────────┘
               │ Events (JSON)
┌──────────────┴────────────────┐
│         Event Sources         │
└──────────────▲────────────────┘    Async ↻
               │ trigger              │
┌──────────────┴────────────────┐  ┌──┴────────────┐
│            Agents             │  │   Services    │
└──────────────▲────────────────┘  └──▲────────────┘
               │ delegate             │ pure utils
┌──────────────┴────────────┐  ┌──────┴─────────────┐
│           Chains          │  │      Tools         │
└──────────────▲────────────┘  └──────▲─────────────┘
               │ call               │ side-effects
┌──────────────┴────────────┐  ┌──────┴─────────────┐
│            Nodes          │  │ External Systems  │
└───────────────────────────┘  └────────────────────┘
```

1. **Event Sources** (e.g. webhook.githubPush) raise events.
2. **Agents** subscribe to these events and decide *what* to do.
3. **Chains** define *how* to do it (sequence, branching, loops).
4. **Nodes** perform *pure* transformations.
5. **Tools** perform side-effects (DB writes, HTTP calls, LLM queries).

---

## Repository Layout

```
.
├── src/
│   ├── ice_sdk/          # Core abstractions – *do not* import `app.*` here
│   └── app/              # Reference implementation
│       ├── agents/
│       ├── chains/
│       ├── nodes/
│       ├── tools/
│       ├── event_sources/
│       └── services/
├── schemas/              # Shared Pydantic models
├── tests/                # Pytest test-suite
├── docs/                 # Additional docs and guides
└── scripts/              # One-off helpers & playgrounds
```

---

## Quick Start

### 1. Prerequisites

* **Python 3.11+** (CPython)
* macOS, Linux, or WSL2
* `make`, `git`, and your preferred `$SHELL`

### 2. Installation

```bash
# Clone the repo
$ git clone https://github.com/stef-writes/iceOSv1-A-.git
$ cd iceOSv1-A-

# Create & activate virtual-env (POSIX)
$ python -m venv .venv && source .venv/bin/activate

# Install dependencies
$ pip install -r requirements.txt

# Optional: install dev extras
$ pip install -r requirements-dev.txt
```

### 3. First Hello-World Agent

```bash
# Execute a demo flow that uses an LLM & prints to console
$ python scripts/test_agent_flow.py
```

Expected output:

```
> 🧊 iceOS booting…
> ⛓️  Running ExampleChain …
Hello, world! I am an iceOS Agent.

---

## Configuration

iceOS uses environment variables for secrets & runtime configuration. The most convenient way is to copy `.env.example` → `.env` and fill in your values.

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Access to OpenAI LLMs |
| `ICE_LOG_LEVEL`  | Log verbosity (`DEBUG`, `INFO`, …) |

Load them automatically with `python-dotenv` (already a dependency).

```bash
cp .env.example .env
export $(cat .env | xargs)  # or use direnv
```

---

## Working With iceOS

### Creating a Node

1. Create `app/nodes/my_cool_node.py`.
2. Derive from `ice_sdk.base.Node`.
3. Define `InputModel` and `OutputModel` with *Pydantic*.
4. Implement `async def run(self, input: InputModel) -> OutputModel`.

```python
from ice_sdk.base import BaseNode
from pydantic import BaseModel, Field

class Input(BaseModel):
    text: str = Field(..., description="User input")

class Output(BaseModel):
    tokens: list[str]

class TokenizeNode(BaseNode[Input, Output]):
    async def run(self, input: Input) -> Output:
        return Output(tokens=input.text.split())
```

### Creating a Tool

*Remember: all external side-effects live here.* The pattern is analogous to Nodes but lives in `app/tools/`.

```python
class GitHubIssueTool(BaseTool[Input, Output]):
    async def run(self, input: Input) -> Output:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/repos/{input.repo}/issues",
                json={"title": input.title, "body": input.body},
                headers={"Authorization": f"Bearer {input.token}"},
            )
            resp.raise_for_status()
            return Output(number=resp.json()["number"])
```

### Building a Chain / Agent

Chains orchestrate Nodes/Tools deterministically; Agents choose which Chain to run.

```python
from app.chains import GreetingChain
from app.agents import GreeterAgent

result = await GreeterAgent().run(name="Ada")
print(result.greeting)
```

---

## Testing & Quality

* **Tests** – `pytest -q`
* **Lint** – `ruff check` (PEP8 & more)
* **Type-check** – `mypy src/`

Automation lives in `Makefile` for convenience:

```bash
make test          # run unit tests
make quality       # lint + mypy
```

CI runs the same commands on every pull request.

---

## Roadmap (next 2 weeks — agility-first)

- [ ] 🏁 *v0.2* – Minimal-Viable Release (safe-mode + PyPI wheel)
- [ ] 🛠️ Developer CLI & hot-reload (`ice new`, `ice run --watch`)
- [ ] 📚 Public API freeze & generated docs
- [ ] 📦 Packaging hygiene (optional extras, manylinux wheel)
- [ ] 💡 Reusable examples library

Full granular checklist lives in [`docs/roadmap_agile.md`](docs/roadmap_agile.md).

---

## Contributing

We love contributions of any size 💙. Please read `CONTRIBUTING.md` for the ground rules.

1. Fork, branch, hack.
2. Write tests & docs.
3. Run `make quality && make test`.
4. Submit a PR — *GitHub Actions* will guide you.

*By contributing you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).*   

---

## License

iceOS is released under the [MIT License](LICENSE).

---

## Deprecation Notices

`ice_tools` currently exists as a *shim* that re-exports classes from `ice_sdk.tools` and `ice_sdk.providers`.

* A `DeprecationWarning` is raised at import-time.
* The shim will be **removed in v0.4** – update your imports today.

---

## Common Tasks

| Task | Command | Notes |
|------|---------|-------|
| Run a Chain | `python scripts/demo_run_chain.py` | Minimal DAG execution *(see scripts folder)* |
| Start API Server | `uvicorn app.api.routes:router --reload` | Local development server |
| Run Tests | `pytest -q` | Quick test execution |
| Health Check | `make doctor` | System diagnostics – detailed matrix in [`docs/healthchecks.md`](docs/healthchecks.md) |
| Update Docs | `make refresh-docs` | Regenerate documentation |
| Start REPL | `python -m ice_sdk.repl` | Interactive SDK shell |
| Deploy API | `docker compose up api` | Production deployment |

---
