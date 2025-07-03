# ice_orchestrator – Workflow Orchestration Engine

## Overview

`ice_orchestrator` is the execution backbone for **IceOS** AI workflows.  It coordinates
nodes, manages data-flow, enforces dependency constraints, and provides first-class
observability for debugging and performance analysis.

*  **Dependency Resolution** – Directed-acyclic graphs with automatic topological
   sorting and cycle detection.
*  **Context Isolation** – Each run receives a dedicated `WorkflowExecutionContext`.
*  **Async Execution** – Nodes run concurrently (level-based) without blocking the
event-loop.
*  **Error Containment** – Fine-grained failure policies (`HALT`, `CONTINUE_POSSIBLE`,
   `ALWAYS`).
*  **Observability** – OpenTelemetry spans plus structured metrics for every node.

## Quick-start

```python
from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.node_models import EchoNodeConfig

# 1. Declare nodes
nodes = [
    EchoNodeConfig(id="hello", prompt="Say hello, {{name}}!"),
]

# 2. Build chain
chain = ScriptChain(nodes=nodes, name="demo")

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