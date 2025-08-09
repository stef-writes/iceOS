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

        # Build a real blueprint: llm -> tool (writer_tool) using Jinja mapping
        bp: Dict[str, Any] = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "llm_to_tool"},
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "name": "research_llm",
                    # Use a generic model id; provider handlers can substitute default if missing
                    "model": "gpt-4-turbo-2024-04-09",
                    "prompt": "Provide concise notes about: {topic}",
                    "llm_config": {"provider": "openai"},
                    "dependencies": [],
                },
                {
                    "id": "t2",
                    "type": "tool",
                    "name": "writer",
                    "tool_name": "writer_tool",
                    "tool_args": {"notes": "{{ llm1.response }}", "style": "executive"},
                    "dependencies": ["llm1"],
                },
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
                "payload": {
                    "blueprint_id": bp_id,
                    "inputs": {"topic": "integration testing"},
                }
            },
        )
        assert r.status_code == 202, r.text
        exec_id = r.json()["execution_id"]

        # Poll
        for _ in range(60):
            await asyncio.sleep(0.2)
            r = await c.get(f"/api/v1/executions/{exec_id}", headers=headers)
            body = r.json()
            if body.get("status") in {"completed", "failed"}:
                # On success we expect writer_tool to produce a summary
                return body
        raise AssertionError("execution did not finish in time")


def test_llm_to_writer_tool_end_to_end() -> None:
    # Ensure FastAPI lifespan runs to register services and tools
    with TestClient(app):
        result = asyncio.run(_run_flow())
        assert result["status"] == "completed"
        out = result["result"]["output"]
        assert "t2" in out
        assert "summary" in out["t2"]
