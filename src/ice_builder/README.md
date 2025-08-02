# ice_builder – Authoring DSL for iceOS

`ice_builder` lets you construct workflows programmatically with full static
typing.  It is the canonical way for humans **and** code-generators (Frosty) to
author nodes, tools, and blueprints.

## Key Modules
| Path | Purpose |
|------|---------|
| `ice_builder.public` | **Stable re-export**.  Only symbols here are guaranteed to stay backward-compatible. |
| `ice_builder.dsl.*` | Fluent APIs (`WorkflowBuilder`, `network`, `agent`, …). |
| `ice_builder.nl.*`  | Natural-language helpers that build `PartialBlueprint`s. |

## Quick Example
```python
from ice_builder.public import WorkflowBuilder

bp = (
    WorkflowBuilder("hello_flow")
    .add_tool("greet", tool_name="hello", name="Ada")
    .build()
)

# Upload via CLI
import json, subprocess, tempfile
with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
    json.dump(bp.model_dump(), f)
    f.flush()
    subprocess.run(["ice", "push", f.name])
```

## Natural-Language Helpers
```python
from ice_builder.nl import create_partial_blueprint, append_tool_node

pb = create_partial_blueprint("hello")
append_tool_node(pb, node_id="greet", tool_name="hello")
blueprint = pb.to_blueprint()
```
These helpers are what Frosty uses internally when converting text to specs.

## Import Rules
Other packages must **import from `ice_builder.public`** – never from internal
sub-modules – to avoid breaking changes.
