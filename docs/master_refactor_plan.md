# iceOS Consolidated Refactor & Split-Up Plan  (v1.0)

*Last updated: 2025-08-06 – reflects `main` after factory-symmetry refactor*

This single document supersedes:

* `docs/refactor_tool_and_agent_symmetry.md`
* `docs/architecture_split_analysis_v0_1.md`

and should be considered the **canonical roadmap** until all tasks are checked-off and the follow-up CHANGELOG is cut.

---
## 0  Legend
✅ = done ▶️ = in-progress ☐ = not started

---
## 1  Registry Symmetry & Factory Migration

| Area | Status |
|------|--------|
| **Agent factory pattern** | ✅ Complete (`register_agent` / `get_agent_instance` + `@agent_factory` decorator + robust testing) |
| **Tool factory pattern** | ✅ Complete (`register_tool_factory` / `get_tool_instance` + `@tool_factory` decorator) |
| **Executors** | ✅ `tool_executor` uses factories; ✅ `agent_executor` uses factories |
| **Builder sugar** | ✅ Complete (`tool_node()` helper; `agent_node()` helper) |
| **CLI scaffolds** | ✅ Complete (`ice new tool/agent/llm-operator` emit factory-based code) |
| **Built-in tool migration** | ✅ Complete (all 11 tools migrated to factory pattern) |
| **Observability** | ☐ Structured warnings / metrics for factories |
| **Robust agent testing** | ✅ Complete (memory, reasoning, planning, real-world scenarios) |

### 1.1 Roadmap (symmetry)

Step | Description | Owner | Status
---- | ----------- | ----- | ------
1 | ✅ Add `@agent_factory` decorator, auto-register with `register_agent` | Core | ✅
2 | ✅ Add `get_agent_instance()` method to complete factory pattern | Core | ✅
3 | ✅ Update agent executor to use factory pattern | Core | ✅
4 | ✅ Add `agent_node()` helper for workflow building | Core | ✅
5 | ✅ Create robust agent tests (memory, reasoning, planning) | Tests | ✅
6 | ✅ Migrate CSV loader to factory pattern | Tools | ✅
7 | ✅ Extend CLI scaffolds (`ice new tool/agent/llm-operator`) to use factories | CLI | ✅
8 | ✅ Migrate all 11 tools to factory pattern | Tools | ✅
9 | Update demos / blueprints to reference factory names | Demo | ☐
10 | Remove legacy singleton code paths (`register_instance` for tools) | Core | ☐

---
## 2  Major Achievements (Completed)

### ✅ **Agent Factory Pattern - COMPLETE**
- **`get_agent_instance()` method** - Added to complete factory pattern symmetry
- **`@agent_factory` decorator** - Auto-registration with validation
- **`agent_node()` helper** - Workflow building symmetry with `tool_node()`
- **Agent executor updated** - Now uses factory pattern instead of singleton
- **Robust agent testing** - Comprehensive tests for memory, reasoning, planning

### ✅ **Tool Factory Migration - COMPLETE**
- **All 11 tools migrated** - Complete migration from singleton to factory pattern
- **Factory validation fixed** - Pydantic validation issues resolved
- **Factory tests added** - Verify factory pattern works correctly
- **Demo updates** - All seller assistant demos now use factory pattern
- **CLI scaffolds updated** - All scaffolds generate factory-based code

### ✅ **Robust Agent Testing - COMPLETE**
- **Memory Integration**: Multi-turn conversations with context persistence
- **Advanced Reasoning**: Inquiry analysis, response planning, tool coordination
- **Real-world Scenarios**: Availability inquiries, price negotiation, status decisions
- **Factory Pattern Validation**: Fresh instances, protocol compliance, error handling

### 📊 **Updated Architecture Status**
| Component | Status | Details |
|-----------|--------|---------|
| **Agent Factory** | ✅ Complete | `register_agent` + `get_agent_instance` + `@agent_factory` |
| **Tool Factory** | ✅ Complete | `register_tool_factory` + `get_tool_instance` + `@tool_factory` |
| **Executors** | ✅ Complete | Both tool and agent executors use factory pattern |
| **Builder Sugar** | ✅ Complete | `tool_node()` + `agent_node()` helpers |
| **Robust Testing** | ✅ Complete | Memory, reasoning, planning, real-world scenarios |
| **Tool Migration** | ✅ Complete | All 11 tools migrated to factory pattern |

---
## 3  Blueprint → Runtime DAG → iceGraph

Object | Essence | Lifecycle | Visible In
------ | ------- | --------- | ----------
**Blueprint** | Immutable JSON (list `NodeSpec` + deps) | Stored by MCP after validation (hash-based `bp_<sha>`) | Edited on **iceCanvas** / **iceStudio**
**Runtime DAG** | `networkx.DiGraph` of validated `NodeConfig`s + run metadata | Built at run start, destroyed after run (or archived for provenance) | Executed by Orchestrator
**iceGraph** | Read-only visualisation of Runtime DAG | Live during run or for post-mortem | iceGraph panel

Immutability & Versioning
* Same Blueprint content ⇒ **same SHA-ID**   (collisions impossible at 96 bits)
* Editing a Blueprint clones it under a new ID (`bp_deadbeef` → `bp_deadbeef_v2`).
* `PartialBlueprint` supports PATCH edits; calling `finalize()` freezes to Blueprint.

---
## 3  Package-Level Split Plan

| Package / File | Current | Target | Status |
| -------------- | ------- | ------ | ------ |
| **Executors** (`ice_orchestrator/execution/executors/unified.py`) | 1 monolith (≈1 300 LOC) | `execution/executors/builtin/*.py` one per node type | ☐ |
| **Builder NL Gen** (`ice_builder/nl/generation/*`) | Two monoliths (`multi_llm_orchestrator.py`, `interactive_pipeline.py`) | Extract to `generation/` sub-package with pure funcs & stage classes | ☐ |
| **Procedural Memory** (`ice_core/memory/procedural.py`) | 1 monolith (≈600 LOC) | Split into `storage.py`, `analytics.py`, `learning.py` | ☐ |
| **Workflow** (`ice_orchestrator/workflow.py`) | Mixed helpers & execution | Create `workflow/` pkg: `model.py`, `graph_utils.py`, `runtime.py` | ☐ |

Sequence recommendation: executors → builder → memory → workflow.

---
## 4  Quality Gates & Principles

1. **Guard the CI gate** – `ruff`, `mypy --strict`, `pytest`, custom layer checks must pass.  
2. **Boy-scout rule** – leave every touched module cleaner.  
3. **Layer boundaries** – no `app.*` imports in `ice_core.*`; cross-layer calls only via `services/*`.  
4. **Strict typing** – no `# type: ignore` unless in vendored stubs.  
5. **Deprecate, don’t duplicate** – thin shim with `@deprecated` + runtime warning.  
6. **Granular commits** – green after each atomic change.  
7. **Contract-first tests** – copy tests before moving code.  
8. **Docs & Registry** – run `gen_catalog.py` after moves.

---
## 5  Testing & Static Analysis

Task | Owner | Status
---- | ----- | ------
Update unit & integration tests for factory flow (≥90 % coverage on new lines) | Tests | ▶️
Run `mypy --strict` across `src/` (scripts/ ignored) | CI | ☐
Add executor-level tests for factory resolution & param passing | Tests | ☐
Update `scripts/check_layers.py`, `check_schema_drift.py` after package moves | DevOps | ☐

---
## 6  Open Risks & Mitigations

Risk | Likelihood | Impact | Mitigation
---- | ---------- | ------ | ----------
Factory pattern breaks existing singleton demos | Med | Med | Provide CLI migration script + keep deprecated decorator until tests are migrated, then remove.
Performance overhead of per-call factory instantiation | Low | Low | Factory caching inside registry + option to mark tool as `stateless=True` for pooling.
Registry refactor introduces circular imports | Low | High | Move helpers to `ice_core.utils` first, add import-cycle test.

---
This master plan replaces the earlier partial docs.  Update check-boxes and statuses directly in this file as work progresses.