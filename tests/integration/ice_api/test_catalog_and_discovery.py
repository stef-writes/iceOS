from __future__ import annotations

from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def test_meta_nodes_catalog_contains_generated_tools_with_hints() -> None:
    # Ensure generated tools are registered
    __import__("ice_tools.generated.lookup_tool")
    __import__("ice_tools.generated.writer_tool")

    res = client.get("/api/v1/meta/nodes")
    assert res.status_code == 200
    data = res.json()
    tools = data.get("tools", [])
    names = {t["name"] for t in tools}
    assert "lookup_tool" in names
    assert "writer_tool" in names

    # Check that at least one tool has ui_hints populated (best-effort)
    any_hints = any("ui_hints" in t and t["ui_hints"] for t in tools)
    assert any_hints

    # Types and schemas endpoints
    res2 = client.get("/api/v1/meta/nodes/types")
    assert res2.status_code == 200
    node_types = res2.json()
    assert "tool" in node_types and "agent" in node_types

    res3 = (
        client.get("/api/v1/meta/nodes/tool/schema")
        if False
        else client.get("/api/v1/meta/nodes/tool/schema")
    )
    # Some frameworks might not expose generic schemas; we at least ensure endpoint works for 'tool' via type-specific
    res3 = client.get("/api/v1/meta/nodes/tool/schema")
    assert res3.status_code == 200
