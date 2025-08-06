"""Register new tools with the MCP `/components/validate` endpoint.

Run this once while the dev server (`make dev`) is up.  It submits the full
source code of each tool so the validator can parse and auto-register them.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import List, Tuple

import httpx


TOOL_SPECS: List[Tuple[str, str, str]] = [
    (
        "facebook_formatter",
        "Format enriched product dict to Facebook Shops payload",
        "src/ice_tools/toolkits/ecommerce/facebook_formatter.py",
    ),
    (
        "api_poster",
        "POST arbitrary JSON payloads to REST endpoint",
        "src/ice_tools/toolkits/common/api_poster.py",
    ),
    (
        "mock_http_bin",
        "Launch local FastAPI HTTP bin for POST testing",
        "src/ice_tools/toolkits/common/mock_http_bin.py",
    ),
]


async def register_tool(name: str, description: str, path: str, client: httpx.AsyncClient) -> None:  # noqa: D401
    """Submit one tool definition and print the result."""
    code = Path(path).read_text()
    payload = {
        "type": "tool",
        "name": name,
        "description": description,
        "tool_class_code": code,
        "auto_register": True,
    }
    response = await client.post(
        "http://localhost:8000/api/v1/mcp/components/validate", json=payload, timeout=None
    )
    try:
        data = response.json()
    except ValueError:
        print(f"[!] {name}: server returned non-JSON – {response.status_code}: {response.text[:200]}")
        return

    status = "✔" if data.get("valid") else "✖"
    print(f"{status}  {name}: registered={data.get('registered')}  errors={data.get('errors')}")


async def main() -> None:  # noqa: D401
    async with httpx.AsyncClient() as client:
        for spec in TOOL_SPECS:
            await register_tool(*spec, client=client)


if __name__ == "__main__":
    asyncio.run(main())
