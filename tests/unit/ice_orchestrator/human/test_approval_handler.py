import asyncio

import pytest

from ice_core.models.node_models import HumanNodeConfig
from ice_orchestrator.human.approval import ApprovalHandler, ApprovalResult

pytestmark = pytest.mark.asyncio


async def test_timeout_escalation(monkeypatch):
    """ApprovalHandler should escalate when timeout occurs and escalation_path is set."""
    cfg = HumanNodeConfig(
        id="h1",
        type="human",
        prompt_message="Please approve",
        timeout_seconds=1,
        escalation_path="workflow:emergency_approval",
    )

    handler = ApprovalHandler(cfg)

    # Patch _wait_for_human_response so it never returns within the timeout
    async def _slow_response(_):
        await asyncio.sleep(2)
        return {"approved": False, "response": "Too late"}

    monkeypatch.setattr(handler, "_wait_for_human_response", _slow_response)

    result: ApprovalResult = await handler.request_approval({})

    assert result.timeout_occurred is True
    assert result.escalated is True
    assert result.approved is False
    assert "Escalated" in result.response
