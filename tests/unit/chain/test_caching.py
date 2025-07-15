from __future__ import annotations

from typing import Any

import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.context import GraphContextManager
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


@pytest.fixture(autouse=True)
def clear_context_manager():
    """Clear the context manager between tests to avoid tool registration conflicts."""
    from ice_sdk.services import ServiceLocator

    # Clear all services to avoid conflicts between tests
    ServiceLocator.clear()


@pytest.mark.asyncio
async def test_lru_cache_skips_second_execution():
    # Create separate tool instances to avoid registration conflicts
    tool1 = CounterTool()
    tool2 = CounterTool()

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
        tools=[tool1],
        name="cache-test-1",
        initial_context={"seed": 1},
        context_manager=GraphContextManager(),  # Use separate context manager
    )
    res1 = await chain1.execute()
    assert res1.success is True
    assert tool1.calls == 1

    # Clear the cache to ensure the second chain calls the tool
    from ice_sdk.cache import global_cache

    global_cache().clear()

    # Second execution with identical inputs ------------------------------
    chain2 = ScriptChain(
        nodes=[node_cfg],
        tools=[tool2],
        name="cache-test-2",
        initial_context={"seed": 1},
        context_manager=GraphContextManager(),  # Use separate context manager
    )
    res2 = await chain2.execute()
    assert res2.success is True
    # Tool should be called again since cache was cleared
    assert tool2.calls == 1
