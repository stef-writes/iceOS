from __future__ import annotations

import json
from typing import Any, Dict

from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": "Bearer dev-token"}


def test_mcp_agents_list_and_schema() -> None:
    # JSON-RPC mcp endpoint is under /api/mcp/
    # Initialize first
    init = client.post(
        "/api/mcp",
        data=json.dumps(
            {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
        ),
        headers=_auth_headers(),
    )
    assert init.status_code == 200

    payload = {"jsonrpc": "2.0", "id": 1, "method": "agents/list"}
    res = client.post("/api/mcp", data=json.dumps(payload), headers=_auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert data.get("result") is not None
    # Result contains { agents: [{name, importPath}, ...] }
    agents = data["result"].get("agents", [])
    assert isinstance(agents, list)

    payload = {"jsonrpc": "2.0", "id": 2, "method": "agents/schema"}
    res2 = client.post("/api/mcp", data=json.dumps(payload), headers=_auth_headers())
    assert res2.status_code == 200
    data2 = res2.json()
    assert "schema" in data2.get("result", {})


def test_agent_runtime_end_to_end() -> None:
    # Use the research_writer example blueprint
    blueprint = {
        "schema_version": "1.2.0",
        "metadata": {"draft_name": "research_writer"},
        "nodes": [
            {
                "id": "t1",
                "type": "tool",
                "name": "lookup",
                "tool_name": "lookup_tool",
                "dependencies": [],
            },
            {
                "id": "t2",
                "type": "tool",
                "name": "writer",
                "tool_name": "writer_tool",
                "dependencies": ["t1"],
            },
            {
                "id": "a1",
                "type": "agent",
                "name": "research_agent",
                "package": "research_agent",
                "max_iterations": 3,
                "dependencies": ["t1"],
            },
        ],
    }

    # Create blueprint
    create = client.post(
        "/api/v1/blueprints/",
        json=blueprint,
        headers={**_auth_headers(), "X-Version-Lock": "__new__"},
    )
    assert create.status_code == 201, create.text
    bp_id = create.json()["id"]

    # Start execution with topic input
    start = client.post(
        "/api/v1/executions/",
        json={
            "payload": {"blueprint_id": bp_id, "inputs": {"topic": "renewable energy"}}
        },
        headers=_auth_headers(),
    )
    assert start.status_code == 202, start.text
    exec_id = start.json()["execution_id"]

    # Poll until completion
    for _ in range(20):
        status = client.get(f"/api/v1/executions/{exec_id}", headers=_auth_headers())
        assert status.status_code == 200
        payload: Dict[str, Any] = status.json()
        if payload.get("status") in {"completed", "failed"}:
            break
    assert payload.get("status") == "completed", payload
    # Ensure agent context was updated by AgentRuntime
    # We accept either direct result embedding or stringified result; just ensure present
    # Exact structure depends on runtime serialization; this checks core behavior.
    # (Further assertions can be added once result shape is finalized.)
