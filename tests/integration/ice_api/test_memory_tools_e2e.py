from __future__ import annotations

import json
import os
from typing import Any, Dict

from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": "Bearer dev-token", "X-Org-Id": "o1", "X-User-Id": "u1"}


def _ensure_plugins_loaded() -> None:
    # Ensure first-party tools manifest is loaded so tool factories register
    import os
    from pathlib import Path

    from ice_core.registry import registry

    manifests = ",".join(
        str(p)
        for p in [
            Path(__file__).parents[3] / "plugins/kits/tools/memory/plugins.v0.yaml",
            Path(__file__).parents[3] / "plugins/kits/tools/search/plugins.v0.yaml",
        ]
    )
    os.environ["ICEOS_PLUGIN_MANIFESTS"] = manifests
    try:
        for m in manifests.split(","):
            registry.load_plugins(m, allow_dynamic=True)
    except Exception:
        pass


def _mcp(method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    res = client.post("/api/mcp/", json=payload, headers=_auth_headers())
    assert res.status_code == 200, res.text
    body = res.json()
    assert "result" in body, body
    return body["result"]


def test_memory_write_and_semantic_search_via_mcp() -> None:
    _ensure_plugins_loaded()

    # Initialize MCP session
    init = client.post(
        "/api/mcp/",
        json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
        headers=_auth_headers(),
    )
    assert init.status_code == 200

    # Ensure hash embedder in test env for determinism
    os.environ["ICEOS_EMBEDDINGS_PROVIDER"] = "hash"

    # Write two documents into semantic memory
    for key, content in [
        ("doc1", "the capital of france is paris"),
        ("doc2", "bananas are yellow fruits"),
    ]:
        _mcp(
            "tools/call",
            {
                "name": "tool:memory_write_tool",
                "arguments": {
                    "inputs": {
                        "key": key,
                        "content": content,
                        "scope": "kb",
                    }
                },
            },
        )

    # Search for a semantically similar query; expect doc1 to rank above doc2
    result = _mcp(
        "tools/call",
        {
            "name": "tool:memory_search_tool",
            "arguments": {
                "inputs": {
                    "query": "france capital",
                    "scope": "kb",
                    "limit": 5,
                }
            },
        },
    )

    # Parse JSON text and tolerate both wrapped and unwrapped tool outputs
    content_items = result.get("content", [])
    assert isinstance(content_items, list) and content_items, result
    text = content_items[0].get("text", "{}")
    payload = json.loads(text)
    rows = payload.get("results") or payload.get("result") or []
    if not rows and isinstance(payload.get("output"), dict):
        only_val = next(iter(payload["output"].values()), {})
        rows = only_val.get("results") if isinstance(only_val, dict) else []
    assert isinstance(rows, list) and rows, payload
    top = rows[0]
    assert top.get("key") == "doc1"
