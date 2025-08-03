# Frosty / iceOS Backend – Hardening Plan **v0.1**  
_“Green-field” hardening: no backwards-compat constraints_

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

### Timeline & Staffing
* Total effort (remaining): **≈ 3 dev-days** (plus 1 day buffer)
* Parallel option: two engineers → finish Phases 3, 4, 5 concurrently in **~2 days**

### Definition of Done
1. `make test` **and** `mypy --strict` green (zero errors).  
2. Coverage ≥ 90 % on changed lines.  
3. Integration test passes end-to-end.  
4. CI guards for protocol, schema and metrics regressions.  
5. No `TODO:` markers remain in code; backlog issues triaged.
