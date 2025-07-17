"""Unit tests verifying ScriptChain's cache toggle behaviour.

The built-in LRU cache should be bypassed when either the *chain-level*
``use_cache`` flag is set to ``False`` **or** a particular node's
``use_cache`` attribute is disabled.  These tests complement
``test_caching.py`` which covers the default (cache-enabled) path.
"""

from __future__ import annotations

from typing import Any

import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.context import GraphContextManager
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.tools.base import BaseTool


class CounterTool(BaseTool):
    """Counts how many times it is actually executed."""

    tool_name = "counter"
    tool_description = "Returns incrementing counter"

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_node_level_cache_disabled():
    """Test that node-level cache setting overrides chain-level setting."""
    tool = CounterTool()

    node_cfg = ToolNodeConfig(
        id="c1",
        name="Counter",
        tool_name="counter",
        retries=0,
        backoff_seconds=0.0,
        use_cache=False,  # Disable cache at node level
    )

    chain = ScriptChain(
        nodes=[node_cfg],
        tools=[tool],
        name="cache-toggle-test",
        initial_context={"seed": 1},
        context_manager=GraphContextManager(),
        use_cache=True,  # Enable cache at chain level
    )

    # First execution
    res1 = await chain.execute()
    assert res1.success is True
    assert tool.calls == 1

    # Second execution with identical inputs
    res2 = await chain.execute()
    assert res2.success is True
    # Tool should be called again since cache is disabled at node level
    assert tool.calls == 2


@pytest.mark.asyncio
async def test_chain_level_cache_disabled():
    """Test that chain-level cache setting affects all nodes."""
    tool = CounterTool()

    node_cfg = ToolNodeConfig(
        id="c1",
        name="Counter",
        tool_name="counter",
        retries=0,
        backoff_seconds=0.0,
        # use_cache defaults to True
    )

    chain = ScriptChain(
        nodes=[node_cfg],
        tools=[tool],
        name="cache-toggle-test",
        initial_context={"seed": 1},
        context_manager=GraphContextManager(),
        use_cache=False,  # Disable cache at chain level
    )

    # First execution
    res1 = await chain.execute()
    assert res1.success is True
    assert tool.calls == 1

    # Second execution with identical inputs
    res2 = await chain.execute()
    assert res2.success is True
    # Tool should be called again since cache is disabled at chain level
    assert tool.calls == 2
