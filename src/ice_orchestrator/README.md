# ice_orchestrator – iceEngine Spatial Computing Runtime

## Overview

`ice_orchestrator` houses the **iceEngine** - the spatial computing powerhouse that drives all iceOS AI workflows. The iceEngine coordinates nodes, manages data-flow, enforces dependency constraints, and provides graph intelligence for both traditional execution and future canvas experiences.

**🎯 Core Features**
*  **NetworkX Graph Intelligence** – Advanced dependency analysis, bottleneck detection, and optimization suggestions
*  **Spatial Computing Ready** – Canvas layout hints, scope organization, and real-time collaboration support  
*  **Frosty AI Integration** – Contextual suggestions and intelligent node recommendations
*  **Level-Based Execution** – Parallel node execution with intelligent scheduling
*  **Context Isolation** – Each run receives a dedicated `WorkflowExecutionContext`
*  **Agent Orchestration** – First-class support for `agent` nodes with memory and tool access
*  **Error Resilience** – Fine-grained failure policies (`HALT`, `CONTINUE_POSSIBLE`, `ALWAYS`)
*  **Advanced Observability** – OpenTelemetry spans, structured metrics, and real-time event streaming

## Quick-start

```python
from ice_orchestrator.workflow import iceEngine
from ice_core.models.node_models import LLMOperatorConfig

# 1. Declare nodes with spatial intelligence
nodes = [
    LLMOperatorConfig(
        id="greet_user", 
        model="gpt-4",
        prompt="Say hello, {{name}}! Provide a warm, personalized greeting.",
        dependencies=[]
    ),
]

# 2. Create iceEngine with spatial features enabled
engine = iceEngine(
    nodes=nodes,
    name="greeting_engine",
    enable_spatial_features=True,
    enable_frosty_integration=True
)

# 3. Execute with spatial intelligence
result = await engine.execute()

# 4. Get graph metrics and optimization suggestions
metrics = engine.get_enhanced_metrics()
suggestions = engine.get_optimization_suggestions()
layout_hints = engine.get_spatial_layout_hints()

# 3. Execute
result = await chain.execute()
print(result.output["hello"].content)
```

## Architecture
```
┌─────────────┐     DAG      ┌─────────────────────────┐
│  NodeConfig │────────────►│  DependencyGraph (nx)   │
└─────────────┘              └─────────┬───────────────┘
                                       │ levels
                                       ▼
                              ┌─────────────────────────┐
                              │   ScriptChainExecutor   │
                              └─────────┬───────────────┘
                                       ▼
                              ┌─────────────────────────┐
                              │ WorkflowExecutionContext│
                              └─────────────────────────┘
```

## Validation
Run static checks before execution:

```python
errors = chain.validate_chain()
if errors:
    raise ValueError("Invalid chain: \n" + "\n".join(errors))
```

## Persistence API
`WorkflowExecutionContext.persist_state(key, state)` batches writes and flushes to
a pluggable store once the buffer reaches `flush_threshold`.

## Development & Testing

1. **Unit tests** – `make test` (see `tests/orchestrator/*`).
2. **Lint & type-check** – `make lint` and `make typecheck`.
3. **Docs** – Update this README and `API_GUIDE.md` for public surfaces.

## License
Apache-2.0 – see `LICENSE` at repo root. 

## Module Structure (v1.1+)

```
 ice_orchestrator/
 ├─ core/           # Core orchestration logic (script_chain, chain_factory)
 ├─ execution/      # Runtime helpers (executor, agent_factory, metrics)
│   ├─ executors/   # Built-in node executors inc. *agent_executor*
 ├─ graph/          # DAG helpers (dependency_graph, level_resolver)
 ├─ utils/          # Pure helpers (context_builder)
 ├─ validation/     # Static & runtime validation helpers
 ├─ errors/         # Exception hierarchy
 ├─ migration/      # Spec up/down-grade helpers
 └─ nodes/          # Node implementations
```

> See `API_GUIDE.md` for public class reference. 