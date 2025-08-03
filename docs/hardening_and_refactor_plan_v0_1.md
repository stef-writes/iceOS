# Hardening & Refactor Plan **v0.1**

> “Green-field” hardening + decomposition: no backwards-compat constraints
>
> This single document replaces the previous `hardening_plan_v0_1.md` **and**
> `refactor_plan_v0_1.md`.  The content is unchanged – only consolidated and
> re-ordered for clarity.  Section anchors remain stable so existing links keep
> working.

---

## Phase 0 – Alignment & Guard-Rails  *(½ day)*
| Step | Status | Description |
|------|--------|-------------|
| 0.1 | ✅ | Kick-off checklist: freeze feature work, create project board `v0.1-hardening`, enable branch-protection |
| 0.2 | ✅ | Enforce layer boundaries – CI job runs `scripts/check_layers.py` |
| 0.3 | ✅ | Dead-code quarantine – `scripts/verify_dead_code.py`, legacy modules removed |
| 0.4 | ✅ | _ToolExecutionSandbox_ shim & entire `_archive/` directory deleted |

Deliverable → pristine tree; tests fail only for known gaps below.

---

## Phase 1 – Protocol Integrity  *(1½ days)*
| Step | Status | Description |
|------|--------|-------------|
| 1.1 | ✅ | `Registry` symmetry: `get_agent_class()`, `list_agents()` + unit tests |
| 1.2 | ✅ | Duplicate `MetricName` enum collapsed; added `EXECUTIONS_FAILED`, `LLM_COST_TOTAL` |
| 1.3 | ✅ | Authenticated & rate-limited `GET /api/v1/blueprints/{id}` with `X-Version-Lock` |
| 1.4 | ✅ | Async-purity audit – blocking calls removed from providers & executors |

---

## Phase 2 – Vector & Memory Safety  *(1 day)*
| Step | Status | Description |
|------|--------|-------------|
| 2.1 | ✅ | Vector-dimension guard + Hypothesis fuzz test |
| 2.2 | ✅ | `MemoryGuarantee` enum enforced; runtime `validate()` + unit tests |
| 2.3 | ✅ | Working / Episodic / Semantic memory token & cost accounting → Prometheus counters |

---

## Phase 3 – API Consistency & Concurrency  *(1 day)*
| Step | Status | Description |
|------|--------|-------------|
| 3.1 | ◇ | Extend optimistic `X-Version-Lock` to **all** mutating blueprint routes |
| 3.2 | ◇ | Schema generator diff-guard in CI (migrate hand-edited JSON) |
| 3.3 | ✅ | Prometheus rule-file generator wired to single `MetricName` enum |

---

## Phase 4 – Sandbox & Defensive Hardening  *(2 days)*
| Step | Status | Description |
|------|--------|-------------|
| 4.1 | ✅ | Unified `ResourceSandbox` (RLIMIT_AS, seccomp, asyncio-timeout) for all executors |
| 4.2 | ◇ | Stress-suite: fork-bomb & large-alloc tools on CI runners |
| 4.3 | ◇ | Expose CPU & memory metrics from sandbox to Prometheus |

---

## Phase 5 – Observability & CI Uplift  *(½ day)*
| Step | Status | Description |
|------|--------|-------------|
| 5.1 | ▶️ | CI matrix: linux/macOS lint (ruff/isort), mypy --strict, tests, coverage ≥ 90 % |
|     |     |  →  mypy errors reduced 120 → ~40 (tracking ticket #hard-mypy) |
| 5.2 | ◇ | One-shot release script `make release-candidate` (freeze deps, run full matrix, docker smoke) |

---

## Phase 6 – End-to-End Validation & RC  *(½ day)*
| Step | Status | Description |
|------|--------|-------------|
| 6.1 | ◇ | Hello-world DSL → MCP API → Orchestrator workflow integration test |
| 6.2 | ◇ | Tag `v0.1.0-rc` with changelog & artefacts |

---

# Codebase Decomposition & Responsibility Plan (v0.1)

> Goal: achieve single-responsibility modules, clear folder boundaries, and
> easier unit-level ownership – without breaking public APIs.

## Target Modules & Extraction Order
| # | Module / Path | Problem | Resolution | New Package Layout |
|---|---------------|---------|------------|--------------------|
| 1 | `src/ice_orchestrator/execution/executors/unified.py` | >350 LOC, holds every built-in executor | **Split per node-type** | `ice_orchestrator/execution/executors/builtin/*` → `tool.py`, `llm.py`, `agent.py`, `condition.py`, `loop.py`, `__init__.py` (re-exports) |
| 2 | `src/ice_builder/nl/generation/multi_llm_orchestrator.py` | Monolithic orchestration, plan parsing, prompt generation, node factory | **Move to orchestrator package** | `ice_builder/nl/orchestrator/plan_parser.py`, `prompt_factory.py`, `node_factories.py`, `orchestrator.py` |
| 3 | `src/ice_core/memory/procedural.py` | Storage, analytics, learning logic intertwined | **Decompose** | `ice_core/memory/procedural/storage.py`, `analytics.py`, `learning.py`, facade `procedural.py` |
| 4 | `src/ice_builder/nl/generation/interactive_pipeline.py` | UI orchestration + parsing mixed | **Stage-class split** | `ice_builder/nl/interactive_pipeline/stages.py`, `pipeline.py`, `io_helpers.py` |
| 5 | `src/ice_orchestrator/workflow.py` & `base_workflow.py` | Helpers + runtime mixed | **Package extraction** | `ice_orchestrator/workflow/model.py`, `graph_utils.py`, `runtime.py`, `__init__.py` |

> *Order chosen for minimal ripple: executors first (isolated), then builder &
> memory, then workflow refactor.*

---

## General Guidelines
* **Public API compatibility**: Add `@deprecated("v0.2", replacement)` shims in original files for one cycle – internal callers updated immediately.
* **Package typing**: every new directory contains `__init__.py` with `from __future__ import annotations` and a `py.typed` marker to keep mypy strict.
* **No cross-layer imports**: helpers stay beside their caller within the same layer.
* **Unit tests**: each new module gets dedicated tests; move existing tests, adapt import paths.
* **CI**: run `make test && mypy --strict` after each extraction commit.

---

## Execution Checklist

1. **Executors split**  
   ☐ Create `builtin/` package  
   ☐ Move functions & register in `__init__.py`  
   ☐ Add shim in old `unified.py` (import-all + deprecation)  
   ☐ Update tests, run CI.

2. **Builder orchestrator breakup**  
   ☐ Create `orchestrator/` package  
   ☐ Extract pure functions (plan → parser, prompt, factories)  
   ☐ Keep thin orchestrator facade  
   ☐ Fix mypy errors (~20)  
   ☐ Tests & CI.

3. **Procedural memory layers**  
   ☐ Write storage class (Redis / file)  
   ☐ Move analytics helpers  
   ☐ Learning adjustments module  
   ☐ Facade composes all three  
   ☐ Update docs & unit tests.

4. **Interactive pipeline stages**  
   ☐ Define `Stage` base class  
   ☐ Move large if/else blocks into concrete stages  
   ☐ Pipeline orchestrates sequence  
   ☐ Update UI hooks.

5. **Workflow package extraction**  
   ☐ Move dataclasses/models to `model.py`  
   ☐ Graph helpers → `graph_utils.py`  
   ☐ Execution runner → `runtime.py`  
   ☐ Deprecate old module  
   ☐ Update orchestrator imports.

---

## Phase 7 – Production Readiness  *(1 day)*
| Step | Status | Description |
|------|--------|-------------|
| 7.1 | ◇ | Structured JSON logging & OpenTelemetry trace correlation |
| 7.2 | ◇ | Secure secrets/config management (Vault/KMS loader, `.env` fallback) |
| 7.3 | ◇ | Dependency & vulnerability scanning (`pip-audit`, `OSV`, Dependabot) |
| 7.4 | ◇ | Automated license scanning wired to CI (`scripts/cli/check_license.py`) |
| 7.5 | ◇ | WebSocket auth & rate-limiting middleware |
| 7.6 | ◇ | Health-check endpoints `/livez`, `/readyz` + graceful shutdown hooks |
| 7.7 | ◇ | Container hardening (non-root UID, distroless base) & SBOM export |
| 7.8 | ◇ | SLA alert rules (error-rate, latency, sandbox kills) → PagerDuty |
| 7.9 | ◇ | Automated DB & Redis backups with restore runbook |
| 7.10 | ◇ | PII redaction policy for logs & memory stores |

---

## Timeline Estimate
| Work-stream | Effort |
|-------------|--------|
| Executors split | 0.5 day |
| Builder orchestrator breakup | 0.75 day |
| Procedural memory layers | 0.5 day |
| Interactive pipeline stages | 0.5 day |
| Workflow extraction | 0.25 day |
| **Subtotal** | **2.5 dev-days** (single engineer) – parallelisable |

---

## Combined Definition of Done (updated)
1. `make test`, `ruff`, `isort`, **and** `mypy --strict` green (zero errors).  
2. Coverage ≥ 90 % on changed lines.  
3. Integration test passes end-to-end (Hello-world DSL → MCP API → Orchestrator).  
4. CI guards for protocol, schema, metrics & layer boundary regressions.  
5. No `TODO:` markers remain; backlog issues triaged.  
6. Deprecation shims slated for removal in v0.2.
