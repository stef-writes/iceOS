# Creating & Registering Tools

## 1. Implement Tool Class
```python
from ice_sdk.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Performs custom action"
    
    parameters_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": string}
        }
    }
    
    async def run(self, param1: str) -> dict:
        return {"result": f"Processed {param1}"}
```

## 2. Register Tool

In your package's `__init__.py`:
```python
from ice_sdk.node_registry import register_tool
from .mytool import MyTool

register_tool(MyTool())
```

## 3. Verify Registration
```bash
curl http://localhost:8000/v1/tools
# Should include "my_tool"
```

**Requirements**
- Inherit from `BaseTool`
- Define `parameters_schema`
- Handle all validation in `run()`
- Register during app startup 

### Frosty Integration

When a **Frosty** meta-agent generates a new tool it should **not** register it directly via private imports.  Instead the agent calls the public helper:

```python
from ice_sdk.node_registry import register_tool
from my_pkg.mytool import MyTool

register_tool(MyTool())
```

Frosty then signals the orchestrator using an event (e.g. `webhook.toolCreated`) so that running chains can hot-load the new capability. 