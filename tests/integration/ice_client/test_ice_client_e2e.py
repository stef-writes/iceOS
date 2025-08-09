from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_client import IceClient


async def _async_flow() -> Dict[str, Any]:
    # Use in-process ASGI transport for speed and determinism
    transport = httpx.ASGITransport(app=app)
    client = IceClient("http://testserver", auth_token="dev-token", transport=transport)

    # Minimal blueprint with placeholder tool node allowed by API validation
    blueprint: Dict[str, Any] = {
        "name": "client_e2e",
        "nodes": [{"id": "n1", "type": "tool"}],
        "metadata": {},
    }

    # Create blueprint
    bp_id, _lock = await client.create_blueprint(blueprint)
    assert isinstance(bp_id, str) and len(bp_id) > 0

    # Start execution
    exec_id = await client.run(blueprint_id=bp_id, inputs={"topic": "demo"})
    assert isinstance(exec_id, str) and len(exec_id) > 0

    # Poll until completion or failure
    final = await client.poll_until_complete(exec_id, timeout=10.0)
    assert final.get("status") in {"completed", "failed"}
    return final


def test_ice_client_e2e() -> None:
    # Ensure FastAPI lifespan is exercised
    with TestClient(app):
        result = asyncio.run(_async_flow())
        assert "status" in result
