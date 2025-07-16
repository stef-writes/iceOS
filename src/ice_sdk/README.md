# ice_sdk – Developer SDK

## Purpose
`ice_sdk` is the primary public surface for _developers_ building on IceOS.
It provides:
* Typed **Node & Tool** abstractions
* A **Provider** layer (LLM, vector, embedding, reranking)
* High-level **Agent** helpers
* A small **runtime** for rendering prompts & counting tokens

> Rule 4: Nothing inside `ice_sdk.*` may import from `app.*` or any
deployment-specific code.

## Quick-start
```python
from ice_sdk.tools.web.http_tool import HttpRequestTool
from ice_sdk.nodes.knowledge.enterprise_kb_node import EnterpriseKBNode
from ice_sdk.chain_builder.engine import ChainBuilder

builder = ChainBuilder("demo_chain")
builder.add_ai_node("ask", prompt="Summarise {{doc}}")
builder.add_tool_node("fetch", tool=HttpRequestTool, url="https://…")
builder.add_node(EnterpriseKBNode("lookup"))
chain = builder.build()
result = await chain.execute()
```

## Package layout
```
ice_sdk/
├─ agents/         # Personas orchestrating workflow logic
├─ tools/          # Idempotent side-effecting actions
├─ providers/      # Concrete adapters (OpenAI, Chroma, Annoy…)
├─ executors/      # Glue: NodeConfig → async coroutine
├─ runtime/        # Prompt renderer, token counter
└─ …
```

## Layer boundary
* Depends _only_ on `ice_core`.
* Exposes **validate()** on every Node/Tool (Rule 13).
* External IO lives strictly inside `tools/` or `providers/`.

## Contributing
```bash
make test   # unit + integration
make type   # mypy --strict
```

## License
MIT. 