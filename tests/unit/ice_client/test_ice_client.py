"""Unit tests for `ice_client.IceClient` that do **not** rely on external
HTTP-mocking libraries.

We stub the network layer using `httpx.MockTransport`, which ships with
httpx itself – no extra dependency needed.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import httpx
import pytest

from ice_client import IceClient, RunStatus
from ice_core.models.mcp import Blueprint, NodeSpec, RunAck, RunResult

BASE_URL = "https://fake-orchestrator"
API_PREFIX = "/api/v1/mcp"


@pytest.mark.asyncio
async def test_submit_blueprint_and_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Full happy-path round-trip: submit → poll (202) → poll (200)."""

    bp = Blueprint(nodes=[NodeSpec(id="n1", type="noop")])
    run_id = "run_1234"

    # ---------------------------------------------------------------------
    # Pre-serialize models so the stub can return raw JSON payloads.
    # ---------------------------------------------------------------------
    ack_payload: dict = RunAck(
        run_id=run_id,
        status_endpoint=f"{API_PREFIX}/runs/{run_id}",
        events_endpoint=f"{API_PREFIX}/runs/{run_id}/events",
    ).model_dump()

    result_payload: dict = RunResult(
        run_id=run_id,
        success=True,
        start_time=datetime.utcnow() - timedelta(seconds=2),
        end_time=datetime.utcnow(),
        output={"hello": "world"},
        error=None,
    ).model_dump(mode="json")

    # ------------------------------------------------------------------
    # Build a state-aware transport handler.
    # ------------------------------------------------------------------
    call_counter: dict[str, int] = {"status": 0}

    def _handler(request: httpx.Request) -> httpx.Response:  # type: ignore[type-arg]
        # POST /runs –> 202 Accepted + RunAck
        if request.method == "POST" and request.url.path == f"{API_PREFIX}/runs":
            return httpx.Response(202, json=ack_payload)

        # GET /runs/{id} –> first 202, then 200 + RunResult
        if (
            request.method == "GET"
            and request.url.path == f"{API_PREFIX}/runs/{run_id}"
        ):
            if call_counter["status"] == 0:
                call_counter["status"] += 1
                return httpx.Response(202)
            return httpx.Response(200, json=result_payload)

        # Anything else –> 404 Not Found (should never happen in this test)
        return httpx.Response(404)

    transport = httpx.MockTransport(_handler)

    # ------------------------------------------------------------------
    # Instantiate client *then* swap its internal AsyncClient for the stub.
    # ------------------------------------------------------------------
    client = IceClient(BASE_URL)
    client._client = httpx.AsyncClient(base_url=BASE_URL, transport=transport)

    ack = await client.submit_blueprint(bp)
    assert ack.run_id == run_id

    status, _ = await client.get_status(run_id)
    assert status in {RunStatus.RUNNING, RunStatus.FINISHED}

    final = await client.wait_for_completion(run_id, poll_interval=0.01)
    assert final.output == {"hello": "world"}

    await client.close()
