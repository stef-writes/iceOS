# iceos – Facade / Ergonomic Top-Level API

## Goal
The `iceos` package is a **thin convenience layer** for scripting and REPL
experimentation.  It re-exports common building blocks and provides fluent
builders (`Chain`, `Node.ai()`, `Node.tool()`, …).

```python
from iceos import Chain, Node, run_chain

chain = (
    Chain("hello")
    .add_node(Node.tool("fetch").tool_name("http_request").tool_args(url="https://…"))
    .add_node(Node.ai("summarise").prompt("Summarise {{fetch.content}}"))
)

result = run_chain(chain)
print(result.output["summarise"].content)
```

## Design Notes
* Depends only on public `ice_sdk` & `ice_orchestrator` APIs.
* **No extra functionality** – just syntactic sugar.
* Safe defaults (persist intermediate outputs, parallelism = 1).

## License
MIT. 