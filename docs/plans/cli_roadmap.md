🚀 **Ice CLI 1.0 – Final Roadmap**

> _Single source of truth for the team's most important TODO_

---

## 0  Guiding Principles

* **Three-Layer Rule**  
  1. Auto-generated SDK parity (thin wrappers)  
  2. Chain / Node / Edge domain verbs  
  3. UX polish (Rich, Typer, completions, Studio TUI)
* Async + Pydantic everywhere; side-effects live only inside Tool impls.
* CLI mirrors SDK → SDK remains the single source of truth.
* No foot-guns: every mutating command supports `--dry-run`/`--yes`.

---

## 1  Architecture Snapshot

```
SDK Core  (Pydantic + OpenAPI)
  │  code-gen
  ▼
Layer 0  Parity        ice <resource> <action>
  │  compose/specialise
  ▼
Layer 1  Domain        chain / node / edge
  │  polish
  ▼
Layer 2  UX            Rich output + Studio TUI
```

---

## 2  12-Week Delivery Schedule

| Phase | Week | Headline                  | Ships & Demo Value |
|-------|------|---------------------------|--------------------|
| 0     | 0    | **Groundwork**            | Binary scaffold, global flags, auth, completions |
| 0     | 0    | **Groundwork**            | Binary scaffold, global flags, auth, completions |
|
### ✅ Progress

* [x] Global context object (`CLIContext`) and top-level Typer callback with `--json`, `--dry-run`, `--yes`, `--verbose` flags implemented (2025-07-01).
* [x] Telemetry event bus + webhook wiring (`CLICommandEvent`, `--no-events`, `.ice/webhooks.yaml`) landed (2025-07-02).
| 1     | 1-2  | **SDK Parity Alpha**      | Core resources (jobs, models, envs, …) |
| 2     | 3-4  | **Chains Exist**          | `chain create\|list\|get`, YAML persistence |
| 3     | 5-6  | **Nodes + Edges MVP**     | `node add`, `edge add`, lint, ASCII graph *(experimental flag)* |
| 4     | 7    | **Tool Ecosystem**        | `tool create`, attach/detach, built-ins pack |
| 5     | 8-9  | **Run & Observe**         | `chain run --watch`, logs follow, stats |
| 6     | 10   | **Guardrails & Tests**    | `chain guard`, `chain test`, CI-friendly exits |
| 7     | 11   | **Chain Studio (TUI)**    | Visual builder, REPL, attack mode |
| 8     | 12   | **DX Polish & Launch**    | Homebrew/PyPI, docs, screen-cast demo |

---

## 3  Feature Checklist

### Lean Core
* 80 % commands are code-generated via OpenAPI → Typer.
* `edge` → `Chain.connect()`, `chain guard` → wraps SDK red-team.

### Cool / Polished
* **5-minute Wow Path**: `ice chain wizard` → `ice chain run --watch`.
* Rich tables, syntax-highlighted JSON, `--mermaid` diagrams.
* Optional bling: `logs follow --rainbow`.

### Robust & Controllable
* Escape hatches: `--raw`, `ICE_LOG=debug`.
* Precision ops (`chain run --node …`).
* Undo & audit log (`~/.ice/ops.log`).

### Future-Proof
* Noun-verb tree → easy plugin slots (`vector-db`, etc.).
* Output formatter registry (`--format=ndjson|html|csv`).
* Plugin market via `ice contrib`.

---

## 4  Chain Studio Highlights

Command | Action
--- | ---
`ice studio open <chain>` | Launch visual builder (keyboard drag-&-drop DAG)
`F1` | Add node (LLM, Agent, Tool wrapper)
`F2` | Connect nodes; pick edge type
`F5` | Run chain live; nodes pulse green on success
`F7` | Open REPL pinned to current node
`F8` | Attack mode (prompt-injection stress test)
`Ctrl + S` | Save YAML + optional Dockerfile
`Ctrl + P` | Copy ASCII/Mermaid diagram to clipboard

**Ships behind** `--experimental-studio` flag initially; graduates when telemetry says "stable".

---

## 5  Cut-Smart Guidance

* **Must-haves for public beta**  → Phases 0-2 + dry-run safety.
* **Phases 3-4** launch as *experimental* if schedule tight.
* Guard & Studio can remain opt-in plugins until v1.1.

---

## 6  Success Criteria

1. **95 % first-run success** (brew install → chain wizard → run).
2. **< 1 week SDK-CLI lag** (enforced by nightly parity CI).
3. **Zero critical regressions** in end-to-end matrix.
4. **"Wow" feedback** in first 10 external user interviews for Chain Studio.

## 7  Webhook Event Integration

CLI commands SHOULD emit structured events so that other subsystems (e.g. webhooks, CI) can react in real-time.

### Standard Event Names
`cli.<command>.<status>`  
Examples: `cli.deploy.started`, `cli.deploy.completed`, `cli.deploy.failed`

### Pydantic Payload Schema

```python
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

class CLICommandEvent(BaseModel):
    command: str
    status: Literal["started", "completed", "failed"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    params: dict[str, Any] = Field(default_factory=dict)
```

### Emission Points
* **Pre-execute** – emit `<command>.started` before any side-effects.
* **Success** – emit `<command>.completed` on a clean exit.
* **Failure** – emit `<command>.failed` on exception path.

> Implementation lives in Tool subclasses; the CLI itself remains side-effect-free in accordance with Guiding Principles & Rule #4.

---

_Last updated_: 2025-07-02 