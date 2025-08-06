# Architecture Split Analysis – v0.1

> Derived from hardening_and_refactor_plan_v0_1.md – verified 2025-08-05 against current `main` tree.

## Refactor and going-forward design principles (to ensure we do not let this happen again)

1. **Guard the CI gate**
   • Every pull-request must pass `ruff`, `mypy --strict`, `pytest`, and custom scripts (`check_layers.py`, `check_schema_drift.py`).
   • Never merge with the gate red – fix or revert.

2. **Boy-scout rule**
   • Touching a module? Leave it cleaner: zero mypy errors, stronger docstrings, no TODOs.

3. **Respect package boundaries**
   • No `app.*` imports inside `ice_core.*` (Rule 4). Cross-layer calls only via `services/*` (Rule 11). `check_layers.py` enforces this automatically.

4. **Strict typing everywhere**
   • New packages include a `py.typed` marker and expose an explicit `__all__`.  
   • No `# type: ignore`s – fix the root cause.

5. **Deprecate, don’t duplicate**
   • After moving code, leave a thin shim with `@deprecated(version="v0.2", replacement="…")` that re-exports the new symbol and logs at runtime.

6. **Granular commits**
   • Split the refactor into atomic commits (e.g., one executor at a time). Each commit must run green locally: `make test && mypy --strict`.

7. **Contract-first testing**
   • Before moving a component, copy its happy-path tests into a new location. Move code only when tests are in place to catch regressions.

8. **Automated duplicate & import checks**
   • Run `python scripts/remove_duplicates.py` to detect copy-paste errors.  
   • Run `python scripts/check_aliases.py` to ensure new sub-packages are imported by their parent `__init__.py`.

9. **Update docs & registry**
   • After relocating executors, run `python scripts/gen_catalog.py` to refresh the registry docs.  
   • Update this analysis doc and CHANGELOG.md in the same PR.

10. **Fail-fast on imports**
    • Use `pytest --import-mode=importlib` to uncover lazy import errors early.  
   • CI runs `python -m pip check` and `scripts/check_input_literals.py` to prevent runtime surprises.

---

## Legend
✅ = already implemented · ▶️ = partially implemented · ☐ = not started

---

## 1. Executor Layer (ice_orchestrator/execution/executors)

| Aspect | Current State | Target / Ideal After Split |
|--------|---------------|----------------------------|
| File layout | `unified.py` (1330 LOC) + `__init__.py` | `builtin/` package with one file per node-type: `tool.py`, `llm.py`, `agent.py`, `condition.py`, `loop.py`, `parallel.py`, `workflow.py`, `code.py`, `recursive.py`, `human.py`, `monitor.py`, `swarm.py` + façade `__init__.py`.  Original `unified.py` kept as thin @deprecated shim importing from new modules. |
| Responsibilities | • Houses **12** async executor functions, Jinja helpers, safe-eval utils, registry bootstrapping<br>• Holds private helpers ` _flatten_dependency_outputs`, `_resolve_jinja_templates`<br>• Directly imports sandbox & registry services | • 1:1 mapping between node-type and executor module (SRP)<br>• Shared helpers (template resolution, param flattening) extracted to `utils.py` inside same package.<br>• Each executor limited to: _validate()_, _execute_impl()_, _post_process()_ to honour Rule 13.
| Layer boundaries | Mixed imports from `ice_core` and `ice_orchestrator` – acceptable | No change – still orchestrator layer, but helpers that belong to core should migrate to `ice_core.utils` to respect Rule 11 eventually.

Result: ☐ **Not started** – no `builtin/` directory detected.

---

## 2. Builder NL Generation (ice_builder/nl/generation)

### 2.1 multi_llm_orchestrator.py

Current:
* Class `MultiLLMOrchestrator` encapsulates **6 pipeline stages** (intent → plan → decomposition → diagram → code → assemble).
* Heavy coupling – holds provider selection, prompt construction, registry look-ups, blueprint assembly.

Ideal:
* Extract pure functions:
  * `plan_parser.py` – parse user spec & planning text.
  * `prompt_factory.py` – template helpers (now in `prompt_templates.py`).
  * `node_factories.py` – map NODE_TYPE_PATTERNS to `ice_core.models`.
* Keep thin façade `orchestrator.py` that wires providers + stages.
* Providers resolved via injected `ProviderFactory` to ease testing.

Status: ☐ **Not started** (file intact, 278 LOC).

### 2.2 interactive_pipeline.py

Current:
* Contains Enum `PipelineStage`, dataclass `PipelineState`, class `InteractiveBlueprintPipeline` (≈300 LOC).
* Logic: user preview / review / execute mixed with IO (DraftStore).

Ideal:
* `interactive_pipeline/stages.py` – individual Stage subclasses implementing `run()`
* `pipeline.py` – orchestrates list[Stage]
* `io_helpers.py` – DraftStore persistence & session handling

Status: ☐ **Not started** (file intact).

---

## 3. Procedural Memory (ice_core/memory/procedural.py)

Current:
* Class `ProceduralMemory` (~600 LOC) implements storage, analytics, learning, and adjustment algorithms.
* Internal dictionaries for metrics, usage, indexes; async CRUD, search, export, learning.

Ideal Decomposition:
* `procedural/storage.py` – CRUD & indexing
* `procedural/analytics.py` – success-metric queries, usage stats
* `procedural/learning.py` – record_execution, apply adjustments, composite procedure synthesis
* Facade `procedural.py` exposes cohesive API, delegates to sub-modules.

Status: ☐ **Not started** (monolith file remains).

---

## 4. Workflow Package Extraction (ice_orchestrator/workflow)

Current:
* Two files at package root: `workflow.py`, `base_workflow.py`.
* Mixed helpers (graph ops), dataclasses, runtime execution methods.

Ideal:
* Create `workflow/` package:
  * `model.py` – dataclasses & Pydantic models
  * `graph_utils.py` – topological helpers currently in `workflow.py`
  * `runtime.py` – run(), retry, metrics, sandbox hooks
* Legacy files become shims with `@deprecated("v0.2", replacement="..." )`.

Status: ☐ **Not started** – structure unchanged.

---

## 5. Interactive Pipeline Stages (builder)

(This is embedded in section 2.2 above) – same split rules apply.

---

## 6. Cross-Cutting Considerations

* **Testing** – each new module mandates unit tests; update paths in `tests/` (search for imports).
* **Mypy** – new sub-packages must include `py.typed` and obey `--strict`.
* **Deprecation** – original modules gain `@deprecated("v0.2", replacement)` decorators and log warnings per Rule 14.
* **Registry Updates** – executor registry looks for modules under `execution.executors.builtin`; ensure `__init__.py` auto-imports executors for eager registration.
* **CI** – modify `scripts/check_layers.py` path map once packages move.

---

## 7. Recommended Next Steps

1. **Kick-off executors split** (lowest coupling):
   * Scaffold `src/ice_orchestrator/execution/executors/builtin/` with `__init__.py`, `utils.py`.
   * Move `tool_executor()` first, adjust imports, add tests, commit ✅.
2. Decompose builder orchestrator in parallel (pure Python, no runtime deps).
3. Procedural memory split (affects analytics tests – ensure coverage).
4. Workflow package extraction last to avoid merge pain with executor work.

---

Generated automatically – please review and adjust before merging.