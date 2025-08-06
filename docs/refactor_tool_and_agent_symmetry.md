# Refactor Plan – Registry Symmetry & Production-Grade Workflow

_This document captures the agreed-upon refactoring steps to bring full symmetry between **agents** and **tools**, improve developer ergonomics, and harden the runtime for production use._

---

## 1. Current State (after recent changes)

| Area | Status |
|------|--------|
| **Agent factory pattern** | Implemented (`register_agent`, `get_agent_instance`) |
| **Agent executor** | Instantiates fresh agent via factory each run |
| **Tool pattern** | Singletons via `register_instance`; no factory support |
| **Memory integration** | Works (UnifiedMemory + `MemoryAgent`) |
| **Demo quality** | Functional but not yet production-hardened |

---

## 2. Asymmetries & Gaps

1. **Tool registration** – Only singleton, no factory‐based instantiation.
2. **Builder UX** – `ice new tool` vs `ice new agent` feel different; WorkflowBuilder lacks helper for tool factories.
3. **Executor inconsistency** – Tool executor still fetches singleton; agents use factory.
4. **Context passing** – Demo bypasses input mapping; outputs are raw dicts.
5. **Memory config** – Low-level knobs require nested configs; ergonomics could improve.
6. **Observability** – Redis fallback OK, but no structured warnings/metrics.

---

## 3. “100 % Power” Target

### A. Symmetric Registry API
```python
registry.register_tool_factory(name, "module:create_func")
registry.get_tool_instance(name_or_path, **kwargs)
```

### B. CLI Scaffolds
* `ice new tool --factory` – mirrors `ice new agent` factory scaffold.
* `ice new workflow` – pre-wires factory-based agents/tools.

### C. WorkflowBuilder Sugar
```python
from ice_builder.utils.tool_factory import tool_node
b.add_node(tool_node("price_calc", factory="pricing_price_calculator"))
```

### D. Executor Upgrades
* Tool executor resolves factory paths via `get_tool_instance`.
* Standard context envelope: `{inputs, memory_ctx, tool_results}`.

### E. Memory Ergonomics
* Helper builder (`MemoryBuilder`) for common configs.
* Validation to block unknown fields.

### F. Observability & Resilience
* Exponential-backoff retry in `LLMService`.
* Structured warnings (`metrics.warn(event="redis_unreachable")`).
* Prometheus hooks for latency & usage.

---

## 4. Implementation Roadmap (bite-sized)

| Step | Description | Owner |
|------|-------------|-------|
| **1** | Add `register_tool_factory` + `get_tool_instance` in `unified_registry.py` | Core |
| **2** | Patch tool executor (unified.py) to use factory path | Orchestrator |
| **3** | Add `tool_node()` helper in `ice_builder.utils.tool_factory` | Builder |
| **4** | Extend `ice new tool` scaffold (`--factory` flag) | CLI |
| **5** | Migrate built-in tools to dual registration (singleton+factory) | Tools |
| **6** | Replace simulated tools in demo with real implementations | Demo |
| **7** | Add retries, tracing, metrics | Core/Observability |
| **8** | Write unit + integration tests for new registry flow | Tests |

_Recommended sequence: 1 → 2 → 3 → 4 (developer UX), then 5-8._

---

## 5. Production-Readiness Checklist

- [ ] Factory pattern for all node types (agents **and** tools)
- [ ] Consistent input/output schemas enforced by validators
- [ ] Memory configuration ergonomics validated
- [ ] Retry/back-off on all external calls (LLM, Redis, HTTP)
- [ ] Structured logging & metrics emitted
- [ ] ≥90 % test coverage on new lines

---

_Last updated: 2025-08-06_
