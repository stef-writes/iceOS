# ice_client – Lightweight Remote Client for iceOS

`ice_client` provides a thin Python wrapper around the iceOS HTTP & WebSocket
API.  It is used by services or scripts that need programmatic access without
pulling in the full orchestration stack.

## Quick Start
```python
from ice_client import IceClient

client = IceClient(base_url="http://localhost:8000")

# List available tools
print(client.list_tools())

# Execute the built-in hello tool
result = client.execute_tool("hello", {"name": "Ada"})
print(result)
```

## Features
* Async and sync APIs (uses `httpx`).
* Automatic retry with exponential backoff.
* Typed Pydantic models mirroring server responses.
* Helper for streaming execution status via WebSocket.

## Roadmap
* Token-auth support once API middleware lands.
* Convenience helpers for uploading blueprints & starting executions (to mirror CLI).
