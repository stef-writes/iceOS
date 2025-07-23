from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_sdk.services.locator import ServiceLocator


# ---------------------------------------------------------------------------
# In-memory Redis stub (minimal subset used by MCP routes) ------------------
# ---------------------------------------------------------------------------


class _MemoryRedis:  # pylint: disable=too-few-public-methods
    _hashes: Dict[str, Dict[str, str]] = {}
    _streams: Dict[str, list[tuple[str, Dict[str, str]]]] = {}

    async def hset(self, key: str, mapping: Dict[str, str]):  # noqa: D401
        self._hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    async def hget(self, key: str, field: str):  # noqa: D401, ANN001
        return self._hashes.get(key, {}).get(field)

    async def exists(self, key: str):  # noqa: D401, ANN001
        return key in self._hashes or key in self._streams

    async def xadd(self, stream: str, data: Dict[str, str]):  # noqa: D401
        lst = self._streams.setdefault(stream, [])
        seq_id = f"{len(lst)}-0"
        lst.append((seq_id, data))
        return seq_id

    async def xread(self, streams, block=0, count=None):  # noqa: D401, ANN001
        results = []
        for stream, last_id in streams.items():
            entries = []
            for seq_id, data in self._streams.get(stream, []):
                if seq_id > last_id:
                    entries.append((seq_id, data))
                    if count and len(entries) >= count:
                        break
            if entries:
                results.append((stream, entries))
        return results

    async def ping(self):  # noqa: D401
        return True


# Inject stub into redis_client singleton before app code uses it -----------
import ice_api.redis_client as _rc

_rc._redis_client = _MemoryRedis()  # type: ignore[attr-defined]


class _StubWorkflowService:  # pylint: disable=too-few-public-methods
    async def execute(  # noqa: D401
        self,
        nodes: list[Any],  # noqa: ANN401 – runtime list
        name: str,
        max_parallel: int = 5,
        *,
        run_id: str | None = None,  # noqa: D401 – keep signature identical
        event_emitter=None,  # noqa: ANN401
    ) -> Dict[str, Any]:
        # Emit a dummy event to simulate node completion
        if event_emitter is not None:
            event_emitter("workflow.node", {"msg": "done"})
        return {"success": True, "output": {"hello": "world"}}


# Register stub so API routes do not call the real orchestrator.
ServiceLocator.register("workflow_service", _StubWorkflowService())

client = TestClient(app)


def _build_minimal_llm_blueprint() -> Dict[str, Any]:
    """Return a minimal, valid blueprint payload as plain dict."""

    node = {
        "id": "n1",
        "type": "llm",
        "model": "gpt-4o",
        "prompt": "Say hi",
        "llm_config": {"provider": "openai"},
    }
    return {"schema_version": "1.1.0", "nodes": [node]}


@pytest.mark.integration
def test_blueprint_registration_success() -> None:
    payload = _build_minimal_llm_blueprint()
    resp = client.post("/api/v1/mcp/blueprints", json=payload)

    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body.get("status") == "accepted"
    assert "blueprint_id" in body


@pytest.mark.integration
def test_blueprint_registration_invalid() -> None:
    # Missing required fields for deterministic tool node → 400
    invalid_node = {"id": "n1", "type": "tool"}
    resp = client.post("/api/v1/mcp/blueprints", json={"nodes": [invalid_node]})
    assert resp.status_code == 400


@pytest.mark.integration
def test_run_inline_blueprint_success() -> None:
    bp_payload = _build_minimal_llm_blueprint()
    run_req = {"blueprint": bp_payload, "options": {"max_parallel": 1}}

    # Start run
    resp_start = client.post("/api/v1/mcp/runs", json=run_req)
    assert resp_start.status_code == 202, resp_start.json()

    run_id = resp_start.json()["run_id"]

    # Retrieve final result (should be immediate thanks to stub)
    resp_result = client.get(f"/api/v1/mcp/runs/{run_id}")
    assert resp_result.status_code == 200, resp_result.json()

    result_body = resp_result.json()
    assert result_body["success"] is True
    assert result_body["output"] == {"hello": "world"} 