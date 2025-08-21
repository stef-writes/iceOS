from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.integration
def test_rag_agent_demo(client) -> None:  # type: ignore[no-redef]
    # Deterministic embeddings in CI
    import os

    os.environ["ICEOS_EMBEDDINGS_PROVIDER"] = "hash"

    # Ingest one tiny file via MCP memory_write_tool
    text = (
        Path("examples/rag_assets/fake_bio.txt").read_text(encoding="utf-8")
    ).strip()
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "tool:memory_write_tool",
            "arguments": {"inputs": {"key": "bio", "content": text, "scope": "kb"}},
        },
    }
    resp = client.post("/api/v1/mcp", json=payload)
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
    assert create.status_code == 200
    bp_id = create.json()["id"]
    run = client.post(
        "/api/v1/executions/",
        json={"blueprint_id": bp_id, "inputs": {"query": "Who is John?"}},
    )
    assert run.status_code == 200
    exec_id = run.json()["execution_id"]

    # Poll until complete
    for _ in range(20):
        st = client.get(f"/api/v1/executions/{exec_id}")
        assert st.status_code == 200
        data = st.json()
        if data.get("status") in {"completed", "failed"}:
            break

    assert data.get("status") == "completed"
    assert isinstance(data.get("result", {}), dict)
