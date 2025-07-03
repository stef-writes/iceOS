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
from ice_sdk.cache import global_cache
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.tools.base import BaseTool


class CounterTool(BaseTool):
    """Test helper that increments a counter on every execution."""

    name: str = "counter"
    description: str = "Returns the current invocation count"

    # Manage call-count as a *model* field so it plays nicely with Pydantic.
    calls: int = 0

    async def run(self, **kwargs: Any):  # type: ignore[override]
        self.calls += 1
        return {"count": self.calls}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_level_cache_disabled() -> None:
    """Disabling cache at the *chain* level should force re-execution."""

    global_cache().clear()  # Ensure a pristine cache between test cases

    tool = CounterTool()
    node_cfg = ToolNodeConfig(id="cn1", name="Counter", tool_name="counter")

    # First run – should invoke the tool once
    chain1 = ScriptChain(
        nodes=[node_cfg],
        tools=[tool],
        name="no-cache-chain-1",
        initial_context={"seed": 1},
        use_cache=False,  # Disable cache globally for this chain
    )
    res1 = await chain1.execute()
    assert res1.success is True
    assert tool.calls == 1

    # Second run with identical inputs – *should* call the tool again
    chain2 = ScriptChain(
        nodes=[node_cfg],
        tools=[tool],
        name="no-cache-chain-2",
        initial_context={"seed": 1},
        use_cache=False,
    )
    res2 = await chain2.execute()
    assert res2.success is True
    assert tool.calls == 2  # ↳ cache bypassed – counter incremented


@pytest.mark.asyncio
async def test_node_level_cache_disabled() -> None:
    """A node with ``use_cache=False`` should bypass the cache even when the
    chain's cache setting remains at its default (enabled).
    """

    global_cache().clear()

    tool = CounterTool()
    node_cfg = ToolNodeConfig(
        id="cn2",
        name="CounterNoCache",
        tool_name="counter",
        use_cache=False,  # Disable cache for this *specific* node
    )

    chain1 = ScriptChain(
        nodes=[node_cfg],
        tools=[tool],
        name="node-no-cache-1",
        initial_context={"seed": 1},
        # *use_cache* not provided – defaults to True at chain level
    )
    await chain1.execute()
    assert tool.calls == 1

    chain2 = ScriptChain(
        nodes=[node_cfg],
        tools=[tool],
        name="node-no-cache-2",
        initial_context={"seed": 1},
    )
    await chain2.execute()
    assert tool.calls == 2  # Cache bypassed again due to node flag
