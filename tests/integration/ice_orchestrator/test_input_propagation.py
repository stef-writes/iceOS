from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx
from fastapi.testclient import TestClient

from ice_api.main import app


async def _run_flow() -> Dict[str, Any]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        headers = {"Authorization": "Bearer dev-token"}

        bp: Dict[str, Any] = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "input_prop"},
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "name": "echo",
                    "model": "gpt-4-turbo-2024-04-09",
                    "prompt": "Echo: {{ inputs.topic }}",
                    "llm_config": {"provider": "openai"},
                    "dependencies": [],
                }
            ],
        }

        r = await c.post(
            "/api/v1/blueprints/",
            headers={**headers, "X-Version-Lock": "__new__"},
            json=bp,
        )
        assert r.status_code in (200, 201), r.text
        bp_id = r.json()["id"]

        r = await c.post(
            "/api/v1/executions/",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "payload": {"blueprint_id": bp_id, "inputs": {"topic": "propagation"}}
            },
        )
        assert r.status_code == 202, r.text
        exec_id = r.json()["execution_id"]

        for _ in range(60):
            await asyncio.sleep(0.2)
            r = await c.get(f"/api/v1/executions/{exec_id}", headers=headers)
            body = r.json()
            if body.get("status") in {"completed", "failed"}:
                return body
        raise AssertionError("execution did not finish in time")


def test_top_level_input_is_available_in_prompt() -> None:
    with TestClient(app):
        body = asyncio.run(_run_flow())
        assert body["status"] == "completed"
        text = body["result"]["output"]["llm1"]["prompt"]
        assert "Echo: propagation" in text
