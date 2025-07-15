import asyncio

import pytest

from ice_sdk.models.config import LLMConfig
from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig
from ice_sdk.utils.perf import WeightedSemaphore, estimate_complexity


@pytest.mark.asyncio
async def test_weighted_semaphore_acquires_and_releases():
    """WeightedSemaphore should acquire *weight* permits on enter and release on exit."""

    sem = asyncio.Semaphore(5)

    # Before entering – full capacity available
    assert sem._value == 5  # type: ignore[attr-defined]

    async with WeightedSemaphore(sem, weight=3):
        # Inside the context, three permits should be consumed
        assert sem._value == 2  # type: ignore[attr-defined]

    # After exit, all permits released
    assert sem._value == 5  # type: ignore[attr-defined]


@pytest.mark.parametrize("weight", [0, -1])
def test_weighted_semaphore_invalid_weight(weight):
    """Weight must be >=1 or a ValueError is raised."""

    sem = asyncio.Semaphore(1)
    with pytest.raises(ValueError):
        WeightedSemaphore(sem, weight=weight)


def test_estimate_complexity_ai_vs_tool():
    """AI nodes should return higher complexity weight than tool nodes."""

    ai_cfg = AiNodeConfig(
        id="ai-1",
        name="ai-node",
        type="ai",
        model="gpt-4o",
        prompt="Hello",
        llm_config=LLMConfig(model="gpt-4o", provider="openai"),
    )

    tool_cfg = ToolNodeConfig(
        id="tool-1", name="tool-node", type="tool", tool_name="echo"
    )

    assert estimate_complexity(ai_cfg) == 2
    assert estimate_complexity(tool_cfg) == 1
