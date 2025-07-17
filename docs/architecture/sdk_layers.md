# SDK Layers

```
ice_sdk
├── agents
├── executors
├── tools
└── providers
```

| Layer | Purpose |
|-------|---------|
| agents      | High-level _node-level_ personas (single-chain) |
| executors   | Glue code mapping nodes → runtime coroutines |
| tools       | Idempotent, side-effecting actions |
| providers   | Low-level LLM / vector / embedder adapters |

> **Composite vs. Orchestrator**  
> Multi-chain coordinators such as `CompositeAgent` **live in**
> `ice_orchestrator.agents` because they depend on the chain registry and
> execution engine.  Similarly, `ChainExecutorTool` moved to
> `ice_orchestrator.tools` for the same reason. The SDK keeps zero imports from
> the orchestrator layer. 