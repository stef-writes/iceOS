from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def _post_json(
    client: httpx.AsyncClient,
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
) -> httpx.Response:
    return await client.post(url, headers=headers, json=payload)


async def _register_echo_llm_and_starter_tools(headers: Dict[str, str]) -> None:
    # Deterministic LLM + ensure starter-pack tools load if referenced
    import os
    from pathlib import Path

    from ice_core.registry import registry
    from ice_core.unified_registry import register_llm_factory
    from ice_orchestrator.config import runtime_config

    register_llm_factory("gpt-4o", "scripts.ops.verify_runtime:create_echo_llm")
    runtime_config.max_tokens = None

    manifests = ",".join(
        str(p)
        for p in [
            Path(__file__).parents[3] / "plugins/kits/tools/memory/plugins.v0.yaml",
            Path(__file__).parents[3] / "plugins/kits/tools/search/plugins.v0.yaml",
        ]
    )
    os.environ["ICEOS_PLUGIN_MANIFESTS"] = manifests
    for m in manifests.split(","):
        registry.load_plugins(m, allow_dynamic=True)


async def test_blueprint_typed_get_patch_put_clone() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        # Minimal blueprint (LLM only)
        bp: Dict[str, Any] = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "typed_models"},
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "Hello {{ inputs.name }}",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                    "output_schema": {"text": "string"},
                    "dependencies": [],
                }
            ],
        }

        # Create
        r = await _post_json(
            c, "/api/v1/blueprints/", bp, {**headers, "X-Version-Lock": "__new__"}
        )
        assert r.status_code in (200, 201), r.text
        create_body = r.json()
        assert set(create_body.keys()) == {"id", "version_lock"}
        bp_id = create_body["id"]

        # GET
        r = await c.get(f"/api/v1/blueprints/{bp_id}", headers=headers)
        assert r.status_code == 200, r.text
        get_body = r.json()
        # Typed response: { data: {...bp...}, version_lock: str }
        assert set(get_body.keys()) == {"data", "version_lock"}
        assert isinstance(get_body["data"], dict)
        assert isinstance(get_body["version_lock"], str)
        server_lock = get_body["version_lock"]
        assert r.headers.get("X-Version-Lock") == server_lock

        # PATCH: update node prompt via NodeSpec replacement
        patch_payload = {
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "Hi {{ inputs.name }}",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                    "output_schema": {"text": "string"},
                    "dependencies": [],
                }
            ]
        }
        r = await c.patch(
            f"/api/v1/blueprints/{bp_id}",
            headers={**headers, "X-Version-Lock": server_lock},
            json=patch_payload,
        )
        assert r.status_code == 200, r.text
        patch_body = r.json()
        assert set(patch_body.keys()) == {"id", "node_count"}
        assert patch_body["id"] == bp_id
        assert isinstance(patch_body["node_count"], int)

        # PUT: replace with current bp data
        r = await c.get(f"/api/v1/blueprints/{bp_id}", headers=headers)
        current = r.json()
        server_lock = current["version_lock"]
        r = await c.put(
            f"/api/v1/blueprints/{bp_id}",
            headers={**headers, "X-Version-Lock": server_lock},
            json=current["data"],
        )
        assert r.status_code == 200, r.text
        put_body = r.json()
        assert set(put_body.keys()) == {"id", "version_lock"}
        assert put_body["id"] == bp_id

        # CLONE: returns typed id/version_lock
        r = await c.post(f"/api/v1/blueprints/{bp_id}/clone", headers=headers)
        assert r.status_code in (200, 201), r.text
        clone_body = r.json()
        assert set(clone_body.keys()) == {"id", "version_lock"}
        assert isinstance(clone_body["id"], str) and clone_body["id"] != bp_id


async def test_executions_typed_status_and_list() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        await _register_echo_llm_and_starter_tools(headers)

        bp: Dict[str, Any] = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "typed_execs"},
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "Ping",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                    "output_schema": {"text": "string"},
                    "dependencies": [],
                }
            ],
        }

        r = await _post_json(
            c, "/api/v1/blueprints/", bp, {**headers, "X-Version-Lock": "__new__"}
        )
        assert r.status_code in (200, 201), r.text
        bp_id = r.json()["id"]

        # Start execution and wait briefly for completion
        r = await c.post(
            "/api/v1/executions/?wait_seconds=5",
            headers={**headers, "Content-Type": "application/json"},
            json={"blueprint_id": bp_id, "inputs": {}},
        )
        assert r.status_code in (200, 202), r.text
        exec_body = r.json()
        assert "execution_id" in exec_body and "status" in exec_body
        exec_id = exec_body["execution_id"]

        # GET typed status
        for _ in range(50):
            rs = await c.get(f"/api/v1/executions/{exec_id}", headers=headers)
            assert rs.status_code == 200, rs.text
            status_obj = rs.json()
            # Required typed keys
            assert "execution_id" in status_obj and "status" in status_obj
            if status_obj["status"] in {"completed", "failed"}:
                break
            await asyncio.sleep(0.1)

        # LIST typed response
        rl = await c.get("/api/v1/executions/", headers=headers)
        assert rl.status_code == 200, rl.text
        lst = rl.json()
        assert "executions" in lst and isinstance(lst["executions"], list)
        assert any(item.get("execution_id") == exec_id for item in lst["executions"])
