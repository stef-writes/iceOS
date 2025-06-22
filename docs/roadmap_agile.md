# iceOS Agile Roadmap — July 2025

The focus is to maximise utility and reusability in the shortest possible time.  
If a task does not improve the experience of **pip install → scaffold a tool → run a chain** within 30 minutes, it belongs in the backlog.

---

## Guiding Principles
1. Ship usable increments weekly (`0.2.x` patch releases).
2. Developer ergonomics trump feature breadth.
3. Freeze public API (`ice_sdk.*`) post-0.2; breaking changes require semver bump.

---

## Milestones

| ETA | Milestone | Key Deliverables |
|-----|-----------|------------------|
| Day 1 | **v0.2 Minimal-Viable Release** | Safe-mode guard (`requires_trust` ➜ 403), version bump, PyPI wheel, example chain + 3-line FastAPI snippet |
| Day 3 | **Developer Loop Polish** | `ice` CLI (`new tool`, `run --watch`), auto-registration of `*.tool.py`, five-minute walk-through docs |
| Day 4 | **Public API Freeze** | Frozen exports, contract test, generated API docs |
| Day 4 | **Packaging Hygiene** | Optional extras for heavy deps, manylinux wheel build, `pip-audit` in CI |
| Day 5 | **Reusable Examples Library** | File summariser, GitHub issue triager, deterministic data-pipeline demos |
| Ongoing | **Community Feedback Loop** | Discussions board, Slack, "good first issue" labels, weekly DX-focused patch releases |

---

## Backlog (deferred)

* Frosty UI & Marketplace
* WASM tool runner
* Advanced Guardrails (token/semantic)
* Planner & Verifier agents 