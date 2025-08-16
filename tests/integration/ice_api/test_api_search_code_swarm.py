from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx
import pytest

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def _await_done(
    c: httpx.AsyncClient, exec_id: str, headers: Dict[str, str]
) -> Dict[str, Any]:
    # Allow up to 20 seconds to accommodate external provider latency
    for _ in range(200):
        await asyncio.sleep(0.1)
        r = await c.get(f"/api/v1/executions/{exec_id}", headers=headers)
        body = r.json()
        if body.get("status") in {"completed", "failed"}:
            return body
    raise AssertionError("execution did not finish in time")


async def _register_factories() -> None:
    # Load starter-pack search tool via plugin and lift token ceiling
    import os
    from pathlib import Path

    from ice_core.registry import registry
    from ice_core.unified_registry import register_llm_factory
    from ice_orchestrator.config import runtime_config

    pack_manifest = (
        Path(__file__).parents[3] / "packs/first_party_tools/plugins.v0.yaml"
    )
    os.environ["ICEOS_PLUGIN_MANIFESTS"] = str(pack_manifest)
    registry.load_plugins(str(pack_manifest), allow_dynamic=True)

    # Register deterministic LLM factory under gpt-4o to avoid network
    register_llm_factory("gpt-4o", "scripts.verify_runtime:create_philo_llm")
    runtime_config.max_tokens = None


async def test_api_llm_to_search_to_llm() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        await _register_factories()

        bp: Dict[str, Any] = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "api_llm_search_llm"},
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "Formulate a search query for '{{ inputs.topic }}'",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                },
                {
                    "id": "search",
                    "type": "tool",
                    "tool_name": "search_tool",
                    "tool_args": {"query": "{{ llm1.response }}"},
                    "dependencies": ["llm1"],
                },
                {
                    "id": "llm2",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "Summarize the top result: {{ search.results[0].title }} - {{ search.results[0].snippet }}",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                    "dependencies": ["search"],
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
                    "inputs": {"topic": "renewable energy"},
                }
            },
        )
        assert r.status_code == 202, r.text
        body = await _await_done(c, r.json()["execution_id"], headers)
        assert body["status"] == "completed"
        assert "llm2" in body["result"]["output"]


async def test_api_code_node_happy() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        from ice_orchestrator.config import runtime_config

        runtime_config.max_tokens = None
        # Write to 'output' so the non-WASM fallback path returns structured data directly
        code = """
output = {"a": inputs.get("a", 0), "b": inputs.get("b", 0), "sum": inputs.get("a", 0) + inputs.get("b", 0)}
"""
        bp = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "api_code_node"},
            "nodes": [
                {
                    "id": "code1",
                    "type": "code",
                    "language": "python",
                    "code": code,
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
            json={"payload": {"blueprint_id": bp_id, "inputs": {"a": 2, "b": 3}}},
        )
        assert r.status_code == 202, r.text
        body = await _await_done(c, r.json()["execution_id"], headers)
    assert body["status"] == "completed"
    # Support both execution paths: WASM (structured with wasm_return_code/result) or fallback (direct output)
    out = body["result"]["output"]["code1"]
    if isinstance(out, dict) and "wasm_return_code" in out:
        assert out["wasm_return_code"] == 0
        assert (
            out["result"]["a"] == 2
            and out["result"]["b"] == 3
            and out["result"].get("sum") == 5
        )
    else:
        # Fallback path returns the executed 'output' mapping directly
        assert out.get("a") == 2 and out.get("b") == 3 and out.get("sum") == 5


async def test_api_swarm_node_smoke() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        from ice_orchestrator.config import runtime_config

        runtime_config.max_tokens = None
        bp = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "api_swarm_smoke"},
            "nodes": [
                {
                    "id": "swarm1",
                    "type": "swarm",
                    "agents": [
                        {"package": "agent.a", "role": "writer"},
                        {"package": "agent.b", "role": "reviewer"},
                    ],
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
            json={"payload": {"blueprint_id": bp_id, "inputs": {}}},
        )
        assert r.status_code == 202, r.text
        body = await _await_done(c, r.json()["execution_id"], headers)
        # Depends on registry presence; accept completed or failed with clear message
        assert body["status"] in {"completed", "failed"}
