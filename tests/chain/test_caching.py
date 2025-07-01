from __future__ import annotations

from typing import Any

import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.tools.base import BaseTool


class CounterTool(BaseTool):
    """Counts how many times it is actually executed."""

    name = "counter"
    description = "Returns incrementing counter"

    calls: int = 0  # pydantic-managed field

    async def run(self, **kwargs: Any):  # type: ignore[override]
        self.calls += 1
        return {"count": self.calls}


@pytest.mark.asyncio
async def test_lru_cache_skips_second_execution():
    tool = CounterTool()

    node_cfg = ToolNodeConfig(
        id="c1",
        name="Counter",
        tool_name="counter",
        retries=0,
        backoff_seconds=0.0,
        # use_cache defaults to True
    )

    # First execution ------------------------------------------------------
    chain1 = ScriptChain(
        nodes=[node_cfg],
        tools=[tool],
        name="cache-test-1",
        initial_context={"seed": 1},
    )
    res1 = await chain1.execute()
    assert res1.success is True
    assert tool.calls == 1

    # Second execution with identical inputs ------------------------------
    chain2 = ScriptChain(
        nodes=[node_cfg],
        tools=[tool],
        name="cache-test-2",
        initial_context={"seed": 1},
    )
    res2 = await chain2.execute()
    assert res2.success is True
    # Tool should **not** be called again thanks to cache -----------------
    assert tool.calls == 1
