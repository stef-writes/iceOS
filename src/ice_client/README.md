# ice_client – Lightweight Remote Client

`ice_client` provides a typed wrapper around the HTTP/JSON-RPC endpoints
exposed by **ice_api** so that external services (or notebooks) can launch and
monitor workflows without importing the full orchestrator stack.

---

## Installation (stand-alone)

```bash
pip install iceos[client]   # only pulls httpx and pydantic
```

When you develop inside the monorepo the package is already on `PYTHONPATH`.

---

## Basic usage

```python
from ice_client.client import ICEClient

client = ICEClient("http://localhost:8000/jsonrpc")

blueprint = {...}  # dict matching mcp.yaml schema
bp_id = client.blueprints.create(blueprint)

exec_id = client.executions.start(bp_id)
print("Execution id", exec_id)

status = client.executions.status(exec_id)
print(status)
```

All methods are *async* under the hood but expose a sync interface for
convenience; set `async_mode=True` if you want raw `asyncio` control.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `ICE_API_URL` | Default server URL if not passed to `ICEClient()` |
| `ICE_API_AUTH_TOKEN` | Bearer token automatically included in headers |

---

## API coverage matrix

| Resource     | Methods                                |
|--------------|----------------------------------------|
| Blueprints   | `list`, `get`, `create`, `delete`      |
| Drafts       | `list`, `save`, `delete`               |
| Executions   | `start`, `status`, `cancel`, `logs`    |

The client intentionally mirrors **ice_api**; for any missing endpoint open an
issue.
