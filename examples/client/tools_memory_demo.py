from __future__ import annotations

import asyncio

from ice_client import IceClient


async def main() -> None:
    client = IceClient()

    # Write two docs via MCP tools/call
    init = await client._client.post(
        "/api/v1/mcp/",
        json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
    )
    init.raise_for_status()

    for key, content in [
        ("doc1", "the capital of france is paris"),
        ("doc2", "bananas are yellow"),
    ]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "tool:memory_write_tool",
                "arguments": {
                    "inputs": {"key": key, "content": content, "scope": "kb"}
                },
            },
        }
        r = await client._client.post("/api/v1/mcp/", json=payload)
        r.raise_for_status()

    # Search via memory_search_tool
    search_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "tool:memory_search_tool",
            "arguments": {
                "inputs": {"query": "france capital", "scope": "kb", "limit": 5}
            },
        },
    }
    sr = await client._client.post("/api/v1/mcp/", json=search_payload)
    sr.raise_for_status()
    print(sr.json())


if __name__ == "__main__":
    asyncio.run(main())
