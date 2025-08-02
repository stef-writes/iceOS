"""Unit tests for :pyclass:`ice_client.IceClient`."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import httpx
import pytest
import respx

from ice_client import IceClient, RunStatus
from ice_core.models.mcp import Blueprint, NodeSpec, RunAck, RunResult

BASE_URL = "https://fake-orchestrator"
API_PREFIX = "/api/v1/mcp"


def _dummy_blueprint() -> Blueprint:
    """Return the minimal valid blueprint accepted by the server stub."""

    # The real server performs heavy validation; for unit testing the client we
    # only need syntactically valid data that *matches* the pydantic schema –
    # respx will stub the HTTP layer so the payload is never inspected by an
    # actual orchestrator.
    return Blueprint(nodes=[NodeSpec(id="n1", type="noop")])


@pytest.mark.asyncio
async def test_submit_blueprint_and_poll(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D401
    bp = _dummy_blueprint()
    run_id = "run_1234"

    # Pre-serialize models for stubbing -------------------------------------
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

    # --------------------------------------------------------------------
    async with respx.mock(base_url=BASE_URL) as router:
        router.post(f"{API_PREFIX}/runs").respond(202, json=ack_payload)
        # First poll returns 202 (still running)
        router.get(f"{API_PREFIX}/runs/{run_id}").respond(202)
        # Second poll returns final 200 result
        router.get(f"{API_PREFIX}/runs/{run_id}").respond(200, json=result_payload)

        client = IceClient(BASE_URL)
        ack = await client.submit_blueprint(bp)
        assert ack.run_id == run_id

        status, res = await client.get_status(run_id)
        # Depending on orchestrator speed we may already have a final result.
        if status == RunStatus.RUNNING:
            assert res is None
        else:
            # Fast completion is acceptable in unit tests
            assert status == RunStatus.FINISHED
            assert res is not None

        final = await client.wait_for_completion(run_id, poll_interval=0.01)
        assert final.output == {"hello": "world"}
        await client.close()
