# Codebase Decomposition & Responsibility Plan (v0.1)

> Goal: achieve single-responsibility modules, clear folder boundaries, and easier unit-level ownership – without breaking public APIs.

---

## Target Modules & Extraction Order

| # | Module / Path | Problem | Resolution | New Package Layout |
|---|---------------|---------|------------|--------------------|
| 1 | `src/ice_orchestrator/execution/executors/unified.py` | >350 LOC, holds every built-in executor | **Split per node-type** | `ice_orchestrator/execution/executors/builtin/\*` → `tool.py`, `llm.py`, `agent.py`, `condition.py`, `loop.py`, `__init__.py` (re-exports) |
| 2 | `src/ice_builder/nl/generation/multi_llm_orchestrator.py` | Monolithic orchestration, plan parsing, prompt generation, node factory | **Move to orchestrator package** | `ice_builder/nl/orchestrator/plan_parser.py`, `prompt_factory.py`, `node_factories.py`, `orchestrator.py` |
| 3 | `src/ice_core/memory/procedural.py` | Storage, analytics, learning logic intertwined | **Decompose** | `ice_core/memory/procedural/storage.py`, `analytics.py`, `learning.py`, facade `procedural.py` |
| 4 | `src/ice_builder/nl/generation/interactive_pipeline.py` | UI orchestration + parsing mixed | **Stage-class split** | `ice_builder/nl/interactive_pipeline/stages.py`, `pipeline.py`, `io_helpers.py` |
| 5 | `src/ice_orchestrator/workflow.py` & `base_workflow.py` | Helpers + runtime mixed | **Package extraction** | `ice_orchestrator/workflow/model.py`, `graph_utils.py`, `runtime.py`, `__init__.py` |

> *Order chosen for minimal ripple: executors first (isolated), then builder & memory, then workflow refactor.*

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

## Timeline Estimate

* **Executors split** – 0.5 day
* **Builder orchestrator** – 0.75 day
* **Procedural memory** – 0.5 day
* **Interactive pipeline** – 0.5 day
* **Workflow extraction** – 0.25 day

_Total ≈ 2.5 dev-days (single engineer); parallelizable across two engineers._

---

### Definition of Done
1. All new packages typed & covered by tests.  
2. `make test`, `ruff`, `isort`, `mypy --strict` pass.  
3. No TODO markers in moved code.  
4. Deprecation shims slated for removal in v0.2.
