# Context & Memory

`SessionState` + `GraphContextManager` orchestrate *global* and *per-node* memory.

```mermaid
sequenceDiagram
    participant User
    participant Router
    participant Agent
    participant Session

    User->>Router: Query (text)
    Router->>Session: read conversation_history
    Router-->>Agent: delegate
    Agent->>Session: read last_outputs
    Agent-->>Agent: LLM / Tool calls
    Agent->>Session: set_output(node_id, output)
    Router->>Session: update last_route
```

## SessionState
Field             | Purpose
------------------|--------------------------------------------------
`conversation_history` | raw user / assistant messages (for chat agents)
`agent_state`     | arbitrary per-agent scratch space (e.g. last route)
`last_outputs`    | map of `agent_name → last successful output`

Backends: In-mem default; swap to Redis/SQLite by serialising `SessionState.to_dict()`.

## GraphContextManager
*Stores intermediate outputs between nodes inside a workflow (DAG).*  
`update_context(node_id, payload)` is called by `LevelBasedScriptChain` whenever a node finishes.  Nodes can declare `input_mappings` to pull data from upstream dependencies.

## Determinism checklist
1. Declare `output_schema` on LLM nodes → downstream tool gets predictable JSON.  
2. Use `input_mappings` to explicitly select source keys.  
3. Enable `use_cache=True` to avoid recomputation.  
4. Set per-node `timeout_seconds`. 