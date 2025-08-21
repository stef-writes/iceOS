from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.integration
def test_rag_agent_demo() -> None:  # type: ignore[no-redef]
    # Deterministic embeddings in CI
    import os

    os.environ["ICEOS_EMBEDDINGS_PROVIDER"] = "hash"

    from starlette.testclient import TestClient

    from ice_api.main import app

    client = TestClient(app)

    # Ingest one tiny file via MCP memory_write_tool
    text = (
        Path("examples/rag_assets/fake_bio.txt").read_text(encoding="utf-8")
    ).strip()
    # Use MCP REST runs API for ingestion to align with production path
    from packs.first_party_agents.rag_agent import rag_chat_blueprint_agent

    # Create a tiny ingestion blueprint via memory_write_tool
    ingest_bp = rag_chat_blueprint_agent(
        model="gpt-4o", scope="kb", top_k=1, with_citations=False
    )
    # Instead of executing the RAG, directly call the MCP JSON-RPC tools/call with initialize first
    init = client.post(
        "/api/v1/mcp/",
        headers={"Authorization": "Bearer dev-token"},
        json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
    )
    assert init.status_code == 200
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "tool:memory_write_tool",
            "arguments": {"inputs": {"key": "bio", "content": text, "scope": "kb"}},
        },
    }
    resp = client.post(
        "/api/v1/mcp/",
        headers={"Authorization": "Bearer dev-token"},
        json=payload,
    )
    assert resp.status_code == 200

    # Build RAG blueprint via first-party agent and run through REST client
    from importlib import import_module

    rag_mod = import_module("packs.first_party_agents.rag_agent")
    bp = getattr(rag_mod, "rag_chat_blueprint_agent")(
        model="gpt-4o", scope="kb", top_k=3, with_citations=False
    )

    # Create and run execution using REST
    create = client.post(
        "/api/v1/blueprints/",
        headers={"X-Version-Lock": "__new__", "Authorization": "Bearer dev-token"},
        json=json.loads(bp.model_dump_json()),
    )
    assert create.status_code == 201
    bp_id = create.json()["id"]
    run = client.post(
        "/api/v1/executions/",
        headers={"Authorization": "Bearer dev-token"},
        json={"blueprint_id": bp_id, "inputs": {"query": "Who is John?"}},
    )
    assert run.status_code in (200, 202)
    exec_id = run.json()["execution_id"]

    # Poll until complete
    for _ in range(20):
        st = client.get(
            f"/api/v1/executions/{exec_id}",
            headers={"Authorization": "Bearer dev-token"},
        )
        assert st.status_code == 200
        data = st.json()
        if data.get("status") in {"completed", "failed"}:
            break

    assert data.get("status") == "completed"
    assert isinstance(data.get("result", {}), dict)
