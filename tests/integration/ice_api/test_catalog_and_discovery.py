from __future__ import annotations

from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def test_meta_nodes_catalog_contains_generated_tools_with_hints() -> None:
    # Ensure starter-pack tools are registered via plugin manifest
    import os
    from pathlib import Path

    from ice_core.registry import registry

    pack_manifest = (
        Path(__file__).parents[3] / "packs/first_party_tools/plugins.v0.yaml"
    )
    os.environ["ICEOS_PLUGIN_MANIFESTS"] = str(pack_manifest)
    # Load dynamically if not already loaded
    registry.load_plugins(str(pack_manifest), allow_dynamic=True)

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
