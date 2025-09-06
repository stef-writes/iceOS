from __future__ import annotations

import json

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def test_ask_my_library_end_to_end() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Initialize MCP
        r = await c.post(
            "/api/mcp/",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
        )
        assert r.status_code == 200

        # Load the bundle workflow YAML and build a blueprint payload
        from pathlib import Path

        import yaml  # type: ignore

        wf_path = Path(
            "/app/plugins/bundles/library_assistant/workflows/ask_my_library.yaml"
        )
        wf_yaml = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        bp = {
            "schema_version": wf_yaml.get("schema_version", "1.2.0"),
            "metadata": {"bundle": "library_assistant.ask_my_library"},
            "nodes": wf_yaml["nodes"],
        }

        # Provide inputs including session/org/user
        inputs = {
            "query": "What is the greeting?",
            "session_id": "sess1",
            "org_id": "o1",
            "user_id": "u1",
        }

        # Pre-load a library asset that the search should retrieve
        lib_url = "/api/v1/library/assets"
        r_lib = await c.post(
            lib_url,
            headers=headers,
            json={
                "label": "greeting",
                "content": "hello world",
                "mime": "text/plain",
                "org_id": "o1",
                "user_id": "u1",
            },
        )
        assert r_lib.status_code == 200, r_lib.text

        # Create blueprint first, then execute via id (executions endpoint requires blueprint_id)
        create = await c.post(
            "/api/v1/blueprints/",
            headers={**headers, "X-Version-Lock": "__new__"},
            json=bp,
        )
        assert create.status_code == 201, create.text
        bp_id = create.json()["id"]
        r_exec = await c.post(
            "/api/v1/executions/",
            headers=headers,
            json={"blueprint_id": bp_id, "inputs": inputs},
        )
        assert r_exec.status_code in (200, 202), r_exec.text
        exec_id = r_exec.json().get("execution_id")
        assert exec_id

        # Poll until completion
        result = None
        for _ in range(60):
            r_status = await c.get(f"/api/v1/executions/{exec_id}", headers=headers)
            assert r_status.status_code == 200
            data = r_status.json()
            if data.get("status") in {"completed", "failed"}:
                result = data
                break
        assert result is not None and result.get("status") == "completed", result

        # Transcript writes are not listed under library assets; ensure execution completed only
