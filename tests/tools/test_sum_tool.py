import pytest

from ice_sdk.tools.base import ToolError
from ice_sdk.tools.builtins.deterministic import SumTool


@pytest.mark.asyncio
async def test_sum_tool_idempotency() -> None:
    """Calling SumTool with the same input twice should yield identical output."""

    tool = SumTool()
    numbers = [1, 2, 3.5]

    result1 = await tool.run(numbers=numbers)
    result2 = await tool.run(numbers=numbers)

    assert result1 == result2  # Full dict equality ensures deterministic output
    assert result1["sum"] == pytest.approx(sum(numbers))


@pytest.mark.asyncio
async def test_sum_tool_invalid_input() -> None:
    """Passing a non-list ``numbers`` argument should raise a ``ToolError``."""

    tool = SumTool()

    with pytest.raises(ToolError):
        await tool.run(numbers="not-a-list")  # type: ignore[arg-type]
