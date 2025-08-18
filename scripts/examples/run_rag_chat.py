from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Mapping

import httpx

from ice_client.client import IceClient
from packs.first_party_tools.rag_blueprint_templates import rag_chat_blueprint


async def main() -> None:
    base_url = os.getenv("ICE_API_URL", "http://localhost:8000")
    token = os.getenv("ICE_API_TOKEN", "dev-token")

    # Use ASGI transport for local dev without network sockets if desired
    transport: httpx.AsyncBaseTransport | None = None

    async with IceClient(base_url, auth_token=token, transport=transport) as client:
        bp = rag_chat_blueprint(model=os.getenv("ICEOS_LLM_MODEL", "gpt-4o"))
        result = await client.run_and_wait(blueprint=bp)
        if not result.success:
            raise SystemExit("RAG chat run failed")
        out: Mapping[str, Any] = result.output
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
