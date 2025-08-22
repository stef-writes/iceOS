# iceos-client

Typed Python client for the iceOS API.

## Install
```bash
pip install iceos-client
```

## Quickstart
```python
import asyncio
from ice_client import IceClient

async def main():
    async with IceClient("http://localhost:8000", auth_token="dev-token") as client:
        # Start a run from an existing blueprint id
        ack = await client.start_execution("bp_abc", inputs={"query": "hi"})
        status = await client.get_execution_status(ack.execution_id)
        print(status.status, status.result)

asyncio.run(main())
```

## Compatibility
- Python 3.11
- See server docs for required environment variables and auth.
