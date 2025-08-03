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

## AI-Powered Natural-Language Builder

`ice_builder.nl` is the new home of **Frosty’s** multi-LLM pipeline.  It turns free-text
specifications into validated `Blueprint` objects while showing an iterative
**Mermaid** preview so users can see the execution graph evolve.

```python
from ice_builder.nl import generate_blueprint_interactive

mermaid, blueprint = generate_blueprint_interactive("Process CSV and email a summary")
print(mermaid)       # ↩ live diagram (can be rendered on Canvas)
print(len(blueprint.nodes))
```

### Interactive flow (future Canvas integration)
1. **Prompt** – The user describes their idea in natural language.
2. **Mermaid Draft** – The NL pipeline creates a draft diagram and returns it
   to the *Canvas* for visual feedback.
3. **Reprompt / Drag-and-Drop** – The user can:
   * Edit the prompt (↺ regenerate)
   * Drag validated **nodes** (registered tools, agents, sub-systems) onto the
     diagram – these become *locked* and cannot be overwritten by the LLM.
4. **Enhance & Validate** – The AI refines the plan, filling in missing
   parameters and connecting the user-placed nodes.
5. **Generate Blueprint** – A fully-validated `Blueprint` is persisted; the
   **Mermaid** diagram (with node IDs) is stored as part of the blueprint’s
   `metadata` so it can be re-hydrated later as a *memory* of the design.

```
user ─▶ idea
          ▼
 AI (LLM) ──▶ Mermaid draft ──▶ Canvas 🖱️  ──▶ refined prompt ──▶ …
```

---

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
