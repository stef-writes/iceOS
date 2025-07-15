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
| agents      | High-level personas controlling workflows |
| executors   | Glue code mapping nodes → runtime coroutines |
| tools       | Idempotent, side-effecting actions |
| providers   | Low-level LLM / vector / embedder adapters |

> **Note**: No module inside `ice_sdk.*` may import from `ice_api.*`. 