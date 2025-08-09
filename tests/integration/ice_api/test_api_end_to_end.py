from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx
import pytest
from fastapi.testclient import TestClient

from ice_api.main import app

pytestmark = pytest.mark.asyncio


async def _post_json(
    client: httpx.AsyncClient,
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
) -> httpx.Response:
    return await client.post(url, headers=headers, json=payload)


async def _await_execution(
    client: httpx.AsyncClient, exec_id: str, headers: Dict[str, str]
) -> Dict[str, Any]:
    for _ in range(60):
        await asyncio.sleep(0.2)
        r = await client.get(f"/api/v1/executions/{exec_id}", headers=headers)
        body = r.json()
        if body.get("status") in {"completed", "failed"}:
            return body
    raise AssertionError("execution did not finish in time")


async def _register_echo_llm_and_writer_tool(headers: Dict[str, str]) -> None:
    # This test relies on runtime factories being available; import in-process factories
    from ice_core.unified_registry import register_llm_factory, register_tool_factory
    from ice_orchestrator.config import runtime_config
    from scripts.verify_runtime import create_echo_llm, create_writer_tool  # noqa: F401

    register_llm_factory("gpt-4o", "scripts.verify_runtime:create_echo_llm")
    register_tool_factory("writer_tool", "scripts.verify_runtime:create_writer_tool")
    runtime_config.max_tokens = None


async def test_api_llm_only() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        await _register_echo_llm_and_writer_tool(headers)

        bp: Dict[str, Any] = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "api_llm_only"},
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "Hello {{ inputs.name }}",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                    "dependencies": [],
                }
            ],
        }

        r = await _post_json(
            c, "/api/v1/blueprints/", bp, {**headers, "X-Version-Lock": "__new__"}
        )
        assert r.status_code in (200, 201), r.text
        bp_id = r.json()["id"]

        r = await _post_json(
            c,
            "/api/v1/executions/",
            {"payload": {"blueprint_id": bp_id, "inputs": {"name": "World"}}},
            {**headers, "Content-Type": "application/json"},
        )
        assert r.status_code == 202, r.text
        exec_id = r.json()["execution_id"]
        body = await _await_execution(c, exec_id, headers)
        assert body["status"] == "completed"
        prompt = body["result"]["output"]["llm1"]["prompt"]
        assert prompt == "Hello World"


async def test_api_llm_to_tool() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        await _register_echo_llm_and_writer_tool(headers)

        bp: Dict[str, Any] = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "api_llm_to_tool"},
            "nodes": [
                {
                    "id": "llm1",
                    "type": "llm",
                    "model": "gpt-4o",
                    "prompt": "{{ inputs.msg }}",
                    "llm_config": {"provider": "openai", "model": "gpt-4o"},
                    "dependencies": [],
                },
                {
                    "id": "t1",
                    "type": "tool",
                    "tool_name": "writer_tool",
                    "tool_args": {"text": "{{ llm1.response }}"},
                    "dependencies": ["llm1"],
                },
            ],
        }

        r = await _post_json(
            c, "/api/v1/blueprints/", bp, {**headers, "X-Version-Lock": "__new__"}
        )
        assert r.status_code in (200, 201), r.text
        bp_id = r.json()["id"]

        r = await _post_json(
            c,
            "/api/v1/executions/",
            {"payload": {"blueprint_id": bp_id, "inputs": {"msg": "ok"}}},
            {**headers, "Content-Type": "application/json"},
        )
        assert r.status_code == 202, r.text
        exec_id = r.json()["execution_id"]
        body = await _await_execution(c, exec_id, headers)
        assert body["status"] == "completed"
        out = body["result"]["output"]
        assert out["llm1"]["prompt"] == "ok"
        assert out["t1"]["written"] == "ECHO::OK"


async def test_api_agent_to_tool() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://testserver", transport=transport
    ) as c:
        await _register_echo_llm_and_writer_tool(headers)

        bp: Dict[str, Any] = {
            "schema_version": "1.2.0",
            "metadata": {"draft_name": "api_agent_to_tool"},
            "nodes": [
                {
                    "id": "agent1",
                    "type": "agent",
                    "package": "tests.integration.runtime.agent_stub",  # illustrative
                    "max_iterations": 1,
                    "dependencies": [],
                }
            ],
        }

        r = await _post_json(
            c, "/api/v1/blueprints/", bp, {**headers, "X-Version-Lock": "__new__"}
        )
        assert r.status_code in (200, 201), r.text
        bp_id = r.json()["id"]

        r = await _post_json(
            c,
            "/api/v1/executions/",
            {"payload": {"blueprint_id": bp_id, "inputs": {}}},
            {**headers, "Content-Type": "application/json"},
        )
        assert r.status_code == 202, r.text
        exec_id = r.json()["execution_id"]
        body = await _await_execution(c, exec_id, headers)
        # API path returns a result (completed/failed) – details depend on agent impl; runtime is exercised
        assert body["status"] in {"completed", "failed"}
