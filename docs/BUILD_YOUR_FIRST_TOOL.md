# Build Your First Tool

This guide walks you through creating a minimal Tool, registering it via Plugins manifest, and using it in a workflow.

## 1) Implement a Tool
Create a factory that returns a `ToolBase` subclass. Example: `plugins.kits.tools.search.writer_tool` already exists; here’s a minimal template:

```python
from __future__ import annotations
from typing import Any, Dict
from pydantic import Field
from ice_core.base_tool import ToolBase

class HelloTool(ToolBase):
    name: str = "hello_tool"
    description: str = Field("Return a greeting for a name")

    async def _execute_impl(self, name: str) -> Dict[str, Any]:
        return {"result": f"Hello, {name}!"}

def create_hello_tool(**kwargs: Any) -> HelloTool:
    return HelloTool(**kwargs)
```

## 2) Add to a Plugins manifest
Create/edit `plugins/kits/tools/hello/plugins.v0.yaml`:

```yaml
schema_version: plugins.v0
components:
  - node_type: tool
    name: hello_tool
    import: plugins.kits.tools.hello.hello_tool:create_hello_tool
    version: 1.0.0
    description: Simple greeting tool
```

## 3) Load manifests
Set env var or compose: `ICEOS_PLUGIN_MANIFESTS=/app/plugins/kits/tools/hello/plugins.v0.yaml,...`

## 4) Use in a blueprint
```json
{
  "schema_version": "1.2.0",
  "nodes": [
    {"id": "say", "type": "tool", "tool_name": "hello_tool", "tool_args": {"name": "Alice"}}
  ]
}
```

POST it to `/api/v1/blueprints` then execute via `/api/v1/executions`.

## Tips
- Input/output schemas are auto-derived from Pydantic fields + `_execute_impl` signature.
- Keep side effects inside tools; use env/config, not globals.
- Validate with MCP `/components/validate` when authoring in Studio.
