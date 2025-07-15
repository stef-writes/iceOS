"""Tests for system tools (SumTool, SleepTool)."""

from __future__ import annotations

import asyncio

import pytest

from ice_sdk.tools.base import ToolError
from ice_sdk.tools.system.sleep_tool import SleepTool  # type: ignore
from ice_sdk.tools.system.sum_tool import SumTool


@pytest.mark.asyncio
async def test_sum_tool_basic() -> None:
    tool = SumTool()
    result = await tool.run(numbers=[1, 2, 3.5])
    assert result == {"sum": 6.5}


@pytest.mark.asyncio
async def test_sum_tool_input_coercion() -> None:
    tool = SumTool()
    # Accept strings convertible to float -----------------------------------
    result = await tool.run(numbers=["4", "1.5"])
    assert result["sum"] == 5.5


@pytest.mark.asyncio
async def test_sum_tool_invalid_element() -> None:
    tool = SumTool()
    with pytest.raises(ToolError):
        await tool.run(numbers=[1, "not-a-number"])  # type: ignore[list-item]


@pytest.mark.asyncio
async def test_sleep_tool_zero_seconds() -> None:
    tool = SleepTool()
    # Sleep with 0 seconds should return almost instantly -------------------
    start = asyncio.get_event_loop().time()
    result = await tool.run(seconds=0)
    elapsed = asyncio.get_event_loop().time() - start

    assert result == {"slept": 0}
    # Ensure wall-clock spent <0.05s so the test stays fast
    assert elapsed < 0.05


@pytest.mark.asyncio
async def test_sleep_tool_bounds_check() -> None:
    tool = SleepTool()
    with pytest.raises(ToolError):
        await tool.run(seconds=-1)
    with pytest.raises(ToolError):
        await tool.run(seconds=61)
