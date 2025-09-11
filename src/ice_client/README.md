# ice_client – Lightweight Remote Client

`ice_client` provides a typed wrapper around the HTTP/JSON-RPC endpoints
exposed by **ice_api** so that external services (or notebooks) can launch and
monitor workflows without importing the full orchestrator stack.

---

## Installation (stand-alone)

```bash
pip install iceos[client]   # pulls httpx and pydantic
```

When you develop inside the monorepo the package is already on `PYTHONPATH`.

---

## Basic usage – run a workflow

```python
from ice_client import IceClient

client = IceClient("http://localhost")

# Preferred helpers (MCP + SSE under the hood)

# 1) Submit and wait for completion
result = await client.run_and_wait(blueprint={
    "schema_version": "1.2.0",
    "metadata": {},
    "nodes": [
        {"id": "t1", "type": "tool", "tool_name": "writer_tool", "tool_args": {"notes": "hi", "style": "concise"}},
        {"id": "llm1", "type": "llm", "provider": "openai", "model": "gpt-4o", "prompt": "Summarize: {{t1.summary}}"},
        {"id": "a1", "type": "agent", "package": "demo_agent", "dependencies": ["llm1"],
         "input_schema": {"message": "str"}, "output_schema": {"reply": "str"}}
    ]
})
print(result.success, result.output)

# 2) Submit and stream live events
async for evt in client.run_and_stream(blueprint_id="bp_123"):
    print("event:", evt)
```

All methods are async; these helpers wrap finalize → submit → poll/SSE for you.

---

## Component creation – from scratch (Studio)

```python
from ice_client import IceClient

client = IceClient()

# 1) Scaffold a new tool source
scaffold = await client.scaffold_component("tool", "csv_loader")
print(scaffold["tool_class_code"])  # present a code editor in the Studio

# 2) Register the component after user edits code
definition = {
    "type": "tool",
    "name": "csv_loader",
    "description": "Load CSV rows",
    "tool_class_code": "...user-edited-code...",
    "auto_register": True,
}
reg = await client.register_component(definition)

# 3) Build a partial blueprint incrementally
pb = await client.create_partial_blueprint()
pb_id = pb["blueprint_id"]
pb, lock = await client.get_partial_blueprint(pb_id)
pb = await client.update_partial_blueprint(pb_id, {"action": "add_node", "node": {"id": "n1", "type": "tool", "tool_name": "csv_loader"}}, version_lock=lock)
pb, lock = await client.get_partial_blueprint(pb_id)
ack = await client.finalize_partial_blueprint(pb_id, version_lock=lock)

# 4) Execute
run_id = await client.submit_blueprint({"blueprint_id": ack["blueprint_id"]})
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `ICE_API_URL` | Default server URL if not passed to `ICEClient()` |
| `ICE_API_TOKEN` | Bearer token automatically included in headers |

---

## API coverage matrix

| Resource     | Methods                                |
|--------------|----------------------------------------|
| Blueprints   | `list`, `get`, `create`, `delete`      |
| Drafts       | `list`, `save`, `delete`               |
| Executions   | `start`, `status`, `cancel`, `logs`    |

The client intentionally mirrors **ice_api**; for any missing endpoint open an
issue.
