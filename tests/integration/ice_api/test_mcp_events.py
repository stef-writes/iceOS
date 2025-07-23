from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_sdk.services.locator import ServiceLocator

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# In-memory Redis stub (shared with other integration tests) -----------------
# ---------------------------------------------------------------------------


class _MemRedis:  # pylint: disable=too-few-public-methods
    _streams: Dict[str, list[tuple[str, Dict[str, str]]]] = {}

    async def xadd(self, stream: str, data: Dict[str, str]):  # noqa: D401
        lst = self._streams.setdefault(stream, [])
        seq_id = f"{len(lst)}-0"
        lst.append((seq_id, data))
        return seq_id

    async def hset(self, *_, **__):  # noqa: D401
        return 1

    async def hget(self, *_, **__):  # noqa: D401
        return None

    async def exists(self, key: str):  # noqa: D401
        return key in self._streams

    async def ping(self):  # noqa: D401
        return True


import ice_api.redis_client as _rc

_rc._redis_client = _MemRedis()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Stub workflow service that emits a node event via event_emitter ------------
# ---------------------------------------------------------------------------


class _StubWFService:  # pylint: disable=too-few-public-methods
    async def execute(
        self,
        *_nodes,  # noqa: D401
        run_id: str | None = None,
        event_emitter=None,
        **__,
    ):
        if event_emitter is not None:
            event_emitter("workflow.node", {"msg": "working"})
        return {"success": True, "output": {"ok": True}}


ServiceLocator.register("workflow_service", _StubWFService())

client = TestClient(app)


def _build_bp() -> Dict[str, Any]:
    node = {
        "id": "n1",
        "type": "llm",
        "model": "gpt-4o",
        "prompt": "Hello",
        "llm_config": {"provider": "openai"},
    }
    return {"schema_version": "1.1.0", "nodes": [node]}


def test_event_stream_records_finished():
    run_req = {"blueprint": _build_bp(), "options": {"max_parallel": 1}}
    resp = client.post("/api/v1/mcp/runs", json=run_req)
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    stream_key = f"stream:{run_id}"
    events = _MemRedis._streams.get(stream_key)
    assert events is not None and len(events) >= 1

    # Last event should be workflow.finished
    _, last_data = events[-1]
    assert last_data["event"] == "workflow.finished" 