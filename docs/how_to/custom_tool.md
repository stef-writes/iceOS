# How-to: Build a Custom Tool

This guide walks through creating **WeatherTool**, a deterministic wrapper around the public `wttr.in` HTTP endpoint.  We will:

1. Scaffold the tool file.
2. Implement the business logic with proper async IO.
3. Declare the JSON parameters schema.
4. Register & test the tool.

---

## 1  Scaffold

Create `weather.tool.py` under any package (e.g. `user_tools/`):

```bash
mkdir -p src/user_tools
$EDITOR src/user_tools/weather.tool.py
```

## 2  Implementation

```python title="src/user_tools/weather.tool.py"
from __future__ import annotations

import httpx
from ice_sdk.tools.base import BaseTool

class WeatherTool(BaseTool):
    """Return the current weather for a given city using *wttr.in*."""

    name = "weather"
    description = "Fetch current weather report for a city (text format)"

    parameters_schema = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "Target city, e.g. 'Berlin'",
            }
        },
        "required": ["city"],
    }

    async def run(self, *, city: str, **_kwargs):  # type: ignore[override]
        url = f"https://wttr.in/{city}?format=3"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            return {"weather": resp.text.strip()}
```

Notes:
* **Type hints** – mandatory by repo rule #1.
* **No blocking IO** – HTTP call uses `httpx.AsyncClient` (rule #5).
* **External side-effects** live only in `run` (rule #2).

## 3  Auto-register

The orchestrator calls `ToolService.discover_and_register(project_root)` during app startup, which imports all `*.tool.py` modules under `src/`.  No further action needed.

## 4  Test the tool

```bash
# CLI smoke test
ice tool test weather -a '{"city": "Berlin"}'

# Within a ScriptChain (YAML excerpt)
- id: weather_step
  type: tool
  tool_name: weather
  tool_args:
    city: Paris
```

You now have a reusable deterministic Tool accessible from Agents, ScriptChains and the HTTP API. 