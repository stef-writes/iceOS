# ice_orchestrator – Workflow Execution Engine

This package executes **DAG workflows** built from `ice_core` NodeConfig
objects.  It is intentionally single-process and async: the goal is fast
iteration for LLM/agent apps rather than cron-style scheduling.

---

## Key concepts

1. **Workflow** (`workflow.py`)
   * Holds an ordered list of nodes and global metadata.
   * `validate()` runs topological + schema checks.
2. **Executors** (`execution/executors/*.py`)
   * One async function per `node.type` registered via
     `@register_node("tool")` decorator.
   * Built-ins: `tool`, `loop`, `parallel`, `condition`, `human`, `monitor`,
     `swarm`, `recursive`.
3. **Context propagation**
   * Each node receives a *shallow copy* of its dependencies’ outputs.
   * Executors never mutate parent contexts – they return a new mapping.
4. **Event bus** (`execution/event_bus.py`)
   * Pub/Sub of `source.eventVerb` events for tracing, metrics & retries.
5. **Retry & sandbox**
   * `execution/retry_policy.py` – exponential back-off with max attempts.
   * `sandbox/resource_sandbox.py` – isolates untrusted binaries & WASM.

---

## Minimal example

```python
from ice_core.models.node_models import ToolNodeConfig
from ice_orchestrator.workflow import Workflow
import ice_orchestrator  # registers executors

nodes = [
    ToolNodeConfig(id="hello", type="tool", tool_name="echo", tool_args={"msg": "hi"})
]
wf = Workflow(nodes, name="demo", version="0.1")
wf.validate()
result = await wf.execute()
print(result.output["hello"])  # → {'msg': 'hi'}
```

---

## Runtime wiring (`ice_core.runtime`)

At process startup, `initialize_orchestrator()` assigns concrete runtime services
to `ice_core.runtime`:

- `workflow_factory`: class used to construct `Workflow` instances
- `network_coordinator_factory`: class used to run network manifests
- `tool_execution_service`: instance used for tool execution
- `context_manager`: shared context manager instance
- `workflow_execution_service`: orchestrator-side service for executing blueprints

Authoring/API layers read these from `ice_core.runtime` to avoid cross-layer imports.

---

## Loop Node fix (2025-08-05)

`loop_executor` was rewritten to directly invoke inner executors, solving the
"empty output" bug that surfaced in the Seller-Assistant demos.

---

## Extending with custom node types

Add a new executor in any importable module:

```python
from ice_orchestrator.execution.executors import register_node

@register_node("my_node")
async def my_executor(workflow, cfg, ctx):
    ...
```

The decorator registers the function in the global mapping so `Workflow` can
resolve it at runtime.

---

## Tests

```bash
pytest tests/unit/ice_orchestrator -q
```

Integration tests cover:
* Loop & recursive flows (`tests/unit/ice_orchestrator/execution/...`)
* Retry logic
* WASM security sandbox

Coverage must stay ≥ 90 %.

---

### WASM code execution (gated)

Code nodes execute in a WASM sandbox when `ICE_ENABLE_WASM=1` and `wasmtime` is installed. The code executor enforces the gate:

```84:92:src/ice_orchestrator/execution/executors/builtin/code_node_executor.py
        # 4. Execute in WASM sandbox (gated by ICE_ENABLE_WASM) -----------
        import os as _os
        if execute_node_with_wasm is None or _os.getenv("ICE_ENABLE_WASM", "1") != "1":
            raise RuntimeError("WASM execution is unavailable; enable ICE_ENABLE_WASM=1 and install 'wasmtime'.")
```

The sandbox implementation lives in `execution/wasm_executor.py` and telemetry in `execution/wasm_resource_monitor.py`.
