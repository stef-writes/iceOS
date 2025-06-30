# ScriptChain Execution Model

ScriptChain executes a directed-acyclic graph in *levels* (topological depth).  Nodes on the same level run concurrently up to `max_parallel`.

Key features:

| Feature | Location | Notes |
|---------|----------|-------|
| Failure policies | `FailurePolicy` enum in `base_script_chain.py` | `CONTINUE_POSSIBLE`, `HALT_ON_ERROR`, etc. |
| Caching | `ice_sdk.cache` | Hashes node inputs + config |
| Guards | `token_guard`, `depth_guard` callbacks | Abort politely when ceilings exceeded |
| Metrics | `ChainMetrics` | Aggregates token / cost per node |
| Observability | OpenTelemetry spans | Integrate with Jaeger / Honeycomb |

Sequence diagram coming soon. 