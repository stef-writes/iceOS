# ice_builder – Workflow Authoring DSL

`ice_builder` offers two ergonomic ways to *create* `ice_orchestrator.workflow.Workflow`
objects so you rarely have to hand-write JSON/YAML.

---

## 1. Fluent `WorkflowBuilder`

```python
from ice_builder.dsl.workflow import WorkflowBuilder

b = WorkflowBuilder("fluent_demo")

# plain tool
b.add_tool("load_csv", tool_name="csv_loader", path="/tmp/data.csv")

# declare dependencies by id reference
b.add_tool(
    "count_rows", tool_name="echo", data={"$ref": "load_csv.rows"},
)

wf = b.to_workflow()
wf.validate()
```

Under the hood `add_tool()` creates a `ToolNodeConfig`.  Similar helpers exist
for `add_loop()`, `add_condition()`, etc.

### Auto-wiring rules
* A node automatically depends on any id referenced via `{"$ref": "node"}`
  or Jinja template `{{ node }}`.
* You can also specify `dependencies=[...]` manually.

---

## 2. Blueprint YAML decorator

```python
from ice_builder.dsl.decorators import blueprint

@blueprint("resources/pricing.yaml")
class PricingBlueprint:  # noqa: D401 – exposed via CLI
    """Generate a simple pricing flow at import-time."""

    def build(self, *, margin: float):
        b = WorkflowBuilder("price_flow")
        b.add_tool("pricing", tool_name="pricing_strategy", margin_percent=margin)
        return b.to_workflow()
```

`ice_cli export-schemas` serialises the generated NodeConfigs into
JSON-Schema-compatible YAML for validation by the MCP layer.

---

## Modules of interest

| Module | Contents |
|--------|----------|
| `dsl.workflow` | `WorkflowBuilder`, helper mixins |
| `dsl.agent` | Agent-specialised builder |
| `dsl.network` | Multi-agent network primitives |
| `nl/` | Natural-language → workflow scaffolds (`atomic_workflow_principles.py` …) |

---

## Tests

`tests/unit/ice_builder` covers builder correctness and NL generation helpers.

```bash
pytest tests/unit/ice_builder -q
```
