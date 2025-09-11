# iceos-client

Typed async Python client for the iceOS Orchestrator API.

## Install

```bash
pip install iceos-client
```

## Quickstart

```python
import asyncio
from ice_client import IceClient

async def main():
    client = IceClient("http://localhost")
    exec_id = await client.run_bundle(
        "chatkit.rag_chat",
        inputs={
            "query": "Two-sentence summary for Stefano.",
            "org_id": "demo_org",
            "user_id": "demo_user",
            "session_id": "chat_demo"
        },
        # If bundle is not pre-registered on the server, auto-register from YAML:
        blueprint_yaml_path="Plugins/bundles/chatkit/workflows/rag_chat.yaml",
        wait_seconds=5,
    )
    print("execution_id:", exec_id)

asyncio.run(main())
```
