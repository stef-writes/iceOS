from __future__ import annotations

from typing import Any

import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.tools.base import BaseTool


class FlakyTool(BaseTool):
    """Tool that raises an exception on the first call, then succeeds."""

    name = "flaky"
    description = "Fails the first time, then returns OK"

    def __init__(self):
        super().__init__()
        self._calls = 0

    async def run(self, **kwargs: Any):  # type: ignore[override]
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("Intentional failure – retry me")
        return {"ok": True, "attempt": self._calls}


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    node_cfg = ToolNodeConfig(
        id="t1",
        name="Flaky",
        tool_name="flaky",
        retries=1,
        backoff_seconds=0.0,
    )

    chain = ScriptChain(
        nodes=[node_cfg],
        tools=[FlakyTool()],
        name="retry-test",
        initial_context={"seed": 42},
    )

    result = await chain.execute()

    assert result.success is True
    assert result.output is not None
    node_result = result.output["t1"]
    assert node_result.success is True
    assert node_result.metadata.retry_count == 1 