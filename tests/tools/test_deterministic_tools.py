import pytest

from ice_sdk.tools.builtins import SleepTool, SumTool


@pytest.mark.asyncio
async def test_sleep_tool_sleeps_return():
    tool = SleepTool()
    result = await tool.run(seconds=0.01)
    assert result == {"slept": 0.01}


@pytest.mark.asyncio
async def test_sum_tool_adds_numbers():
    tool = SumTool()
    numbers = [1, 2, 3.5]
    result = await tool.run(numbers=numbers)
    assert result == {"sum": sum(numbers)}
