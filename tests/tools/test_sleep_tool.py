import pytest

from ice_sdk.tools.builtins.deterministic import SleepTool, deterministic_summariser


@pytest.mark.asyncio
async def test_sleep_tool_zero() -> None:
    """SleepTool with zero seconds should return immediately."""

    tool = SleepTool()

    # Run with seconds=0 to avoid real delay
    result = await tool.run(seconds=0)

    assert result == {"slept": 0}


@pytest.mark.asyncio
async def test_sleep_tool_invalid_range() -> None:
    """SleepTool should raise when given out-of-range seconds."""

    tool = SleepTool()

    with pytest.raises(Exception):
        await tool.run(seconds=-1)


def test_deterministic_summariser() -> None:
    """deterministic_summariser should truncate long text and append ellipsis."""

    long_text = "a" * 200
    summary = deterministic_summariser(long_text, max_tokens=10)

    # Output should be shorter than input and contain ellipsis
    assert len(summary) < len(long_text)
    assert summary.endswith("…") or summary.endswith("...")
