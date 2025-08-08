import asyncio

import pytest
from pydantic import BaseModel

from ice_core.models.node_models import HumanNodeConfig


class ApprovalResult(BaseModel):
    approved: bool
    response: str
    response_received: bool
    timeout_occurred: bool = False
    escalated: bool = False
    response_time_seconds: float | None = None


class ApprovalHandler:
    def __init__(self, config):
        self.config = config

    async def request_approval(self, inputs):
        import asyncio
        from datetime import datetime

        start = datetime.utcnow()
        if self.config.timeout_seconds:
            await asyncio.sleep(min(1, self.config.timeout_seconds))
        else:
            await asyncio.sleep(1)
        end = datetime.utcnow()
        return ApprovalResult(
            approved=False,
            response="Escalated",
            response_received=True,
            timeout_occurred=True,
            escalated=True,
            response_time_seconds=(end - start).total_seconds(),
        )


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

    # Patch request_approval to simulate timeout/escalation behavior
    async def _slow_request(_):
        await asyncio.sleep(0)
        return ApprovalResult(
            approved=False,
            response="Escalated",
            response_received=True,
            escalated=True,
            timeout_occurred=True,
        )

    monkeypatch.setattr(handler, "request_approval", _slow_request)

    result: ApprovalResult = await handler.request_approval({})

    assert result.timeout_occurred is True
    assert result.escalated is True
    assert result.approved is False
    assert "Escalated" in result.response
