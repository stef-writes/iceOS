from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Mapping, Sequence

import httpx

from ice_client.client import IceClient
from packs.first_party_tools.rag_blueprint_templates import rag_chat_blueprint


async def main() -> None:
    base_url = os.getenv("ICE_API_URL", "http://localhost:8000")
    token = os.getenv("ICE_API_TOKEN", "dev-token")

    # Use ASGI transport for local dev without network sockets if desired
    transport: httpx.AsyncBaseTransport | None = None

    org_id = os.getenv("ICE_DEFAULT_ORG_ID", "demo_org")
    user_id = os.getenv("ICE_DEFAULT_USER_ID", "demo_user")

    async with IceClient(base_url, auth_token=token, transport=transport) as client:
        # 1) Ingest a few facts
        ingest_docs: Sequence[str] = [
            "Paris is the capital of France.",
            "Bananas are yellow fruits.",
            "Raspberries are red and tart.",
        ]
        for text in ingest_docs:
            # Call ingestion via MCP tools/call
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "tool:ingestion_tool",
                    "arguments": {
                        "inputs": {
                            "source_type": "text",
                            "source": text,
                            "scope": "kb",
                            "org_id": org_id,
                            "user_id": user_id,
                        }
                    },
                },
            }
            async with client._client as http:  # reuse underlying httpx client
                resp = await http.post("/api/mcp", json=payload)
                resp.raise_for_status()

        # 2) Build RAG chat blueprint
        bp = rag_chat_blueprint(model=os.getenv("ICEOS_LLM_MODEL", "gpt-4o"))

        # 3) Run one query with org/user inputs for scoping
        result = await client.run_and_wait(blueprint=bp)
        if not result.success:
            raise SystemExit("RAG chat run failed")
        out: Mapping[str, Any] = result.output
        print("RAG Output:")
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
