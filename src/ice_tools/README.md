# ice_tools – Built-in and User-Defined Tools for iceOS

`ice_tools` is the canonical location for **runtime tool implementations**.
Tools are stateless, idempotent operations that the orchestrator can call as
part of a workflow.

The package currently ships with a single sample tool (`HelloTool`) that helps
smoke-test a fresh iceOS deployment, but the directory structure is designed to
host dozens (or hundreds) of production-grade tools.

## Directory Layout
```
src/ice_tools/
  __init__.py     ← auto-imports all sub-modules so their @tool decorators run
  hello.py        ← sample HelloTool implementation
  README.md       ← you are here
  <your_tool>.py  ← put additional tools here
```

## Creating a New Tool
1. **Inherit** from `ice_core.base_tool.ToolBase`.
2. **Implement** `_execute_impl()` as an async method (it will be wrapped).
3. **Annotate** with the `@tool` decorator from `ice_builder.public` *or*
   call `registry.register_instance()` manually.

```python
# src/ice_tools/csv_reader.py
from typing import Any, Dict

from ice_builder.public import tool  # re-export of decorator
from ice_core.base_tool import ToolBase

@tool()  # name defaults to "csv_reader"
class CSVReaderTool(ToolBase):
    """Reads a CSV file and returns rows as JSON."""

    name: str = "csv_reader"
    description: str = "Read a CSV file from disk or URL."

    async def _execute_impl(self, *, path: str, delimiter: str = ",", **_: Any) -> Dict[str, Any]:
        import pandas as pd
        df = pd.read_csv(path, delimiter=delimiter)
        return {"rows": df.to_dict(orient="records")}
```

On import, the decorator registers an *instance* of the tool inside the global
registry, making it immediately discoverable:

```bash
curl http://localhost:8000/api/v1/tools
# → ["hello", "csv_reader", …]
```

## Input & Output Schemas
`ToolBase` supports optional static methods `get_input_schema()` and
`get_output_schema()`.  If implemented, these JSON schemas will be surfaced to
UIs and validation layers.

```python
    @classmethod
    def get_input_schema(cls):
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "delimiter": {"type": "string", "default": ","},
            },
            "required": ["path"],
        }
```

## Import Rules & Layer Boundaries
* `ice_tools` **may only import** from `ice_core` and standard-library modules.
* Tool implementations must keep external side-effects *inside* `_execute_impl`
  (rule #2 in project guidelines).

## Roadmap
* Add a `LongRunningToolBase` subclass for tools that stream progress.  The
  registry will then mark such tools as `progress_capable=True` to enable UI
  progress bars.
