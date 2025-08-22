# Client Quickstart

## Install
```bash
pip install iceos-client
```

## Configure
Set environment variables (or pass explicitly to `IceClient`):
```bash
export ICE_API_URL=http://localhost:8000
export ICE_API_TOKEN=dev-token
```

## Run a ChatKit workflow
```python
import asyncio
from ice_client import IceClient

async def main():
    async with IceClient() as client:
        exec_id = await client.run(
            blueprint_id="chatkit.rag_chat",
            inputs={"query":"Summarize me","org_id":"demo_org","user_id":"demo_user","session_id":"s1"}
        )
        final = await client.poll_until_complete(exec_id, timeout=60)
        print(final)

asyncio.run(main())
```

## Tools demo
See `examples/client/tools_memory_demo.py` for writing documents and searching via memory tools.

## Agent chat demo
See `examples/client/agent_demo.py` for a data-first agent chat turn.
