from __future__ import annotations

import asyncio
import json

from ice_client import IceClient


async def main() -> None:
    client = IceClient()

    # Ingest a small sample via MCP
    init = await client._client.post(
        "/api/v1/mcp/",
        json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
    )
    init.raise_for_status()
    text = "Paris is the capital of France."
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "tool:memory_write_tool",
            "arguments": {"inputs": {"key": "fact", "content": text, "scope": "kb"}},
        },
    }
    r = await client._client.post("/api/v1/mcp/", json=payload)
    r.raise_for_status()

    # Run ChatKit Bundle workflow
    exec_id = await client.run(
        blueprint_id="chatkit.rag_chat",
        inputs={
            "query": "What is the capital of France?",
            "org_id": "demo_org",
            "user_id": "demo_user",
            "session_id": "s1",
        },
    )
    final = await client.poll_until_complete(exec_id, timeout=60)
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
