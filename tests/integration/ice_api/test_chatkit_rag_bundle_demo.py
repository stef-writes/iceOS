from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


@pytest.mark.integration
def test_chatkit_rag_bundle_e2e() -> None:  # type: ignore[no-redef]
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
    # Use MCP JSON-RPC tools/call to write content (no legacy agent dependency)
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

    # Load plugin manifests for first-party tools (memory/search) and register echo LLM
    import os
    from pathlib import Path as _P

    from ice_core.unified_registry import register_llm_factory as _reg_llm
    from ice_core.unified_registry import registry as _reg

    manifests = ",".join(
        str(p)
        for p in [
            _P(__file__).parents[3] / "plugins/kits/tools/memory/plugins.v0.yaml",
            _P(__file__).parents[3] / "plugins/kits/tools/search/plugins.v0.yaml",
        ]
    )
    os.environ["ICEOS_PLUGIN_MANIFESTS"] = manifests
    for m in manifests.split(","):
        _reg.load_plugins(m, allow_dynamic=True)
    _reg_llm("gpt-4o", "scripts.ops.verify_runtime:create_echo_llm")

    # Build a blueprint from the ChatKit Bundle workflow (rag_chat.yaml) and run it
    rag_path = (
        _P(__file__).parents[3] / "plugins/bundles/chatkit/workflows/rag_chat.yaml"
    )
    rag_yaml = yaml.safe_load(rag_path.read_text(encoding="utf-8"))
    bp = {
        "schema_version": rag_yaml.get("schema_version", "1.2.0"),
        "metadata": {"draft_name": "chatkit_rag_chat"},
        "nodes": rag_yaml["nodes"],
    }

    create = client.post(
        "/api/v1/blueprints/",
        headers={
            "X-Version-Lock": "__new__",
            "Authorization": "Bearer dev-token",
            "Content-Type": "application/json",
        },
        json=bp,
    )
    assert create.status_code in (200, 201), create.text
    bp_id = create.json()["id"]
    inputs = {
        "org_id": "demo_org",
        "user_id": "demo_user",
        "session_id": "s1",
        "query": "Who is John?",
    }
    run = client.post(
        "/api/v1/executions/",
        headers={
            "Authorization": "Bearer dev-token",
            "Content-Type": "application/json",
        },
        json={"blueprint_id": bp_id, "inputs": inputs},
    )
    assert run.status_code in (200, 202)
    exec_id = run.json().get("execution_id")

    # Poll until complete (allow brief time for async execution)
    import time as _t

    for _ in range(60):
        st = client.get(
            f"/api/v1/executions/{exec_id}",
            headers={"Authorization": "Bearer dev-token"},
        )
        assert st.status_code == 200
        data = st.json()
        if data.get("status") in {"completed", "failed"}:
            break
        _t.sleep(0.2)

    assert data.get("status") == "completed"
    assert isinstance(data.get("result", {}), dict)
