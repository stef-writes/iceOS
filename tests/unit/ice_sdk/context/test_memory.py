
import pytest

from ice_orchestrator.context.memory import NullMemory

pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
async def test_null_memory_roundtrip() -> None:
    """NullMemory should accept calls but never return stored data."""

    mem = NullMemory()
    # Async helpers -----------------------------------------------------
    await mem.add("hello")
    res = await mem.retrieve("hello")
    # Null adapter always yields empty list
    assert res == []

    # Synchronous vector helpers should be no-ops and not raise.
    mem.store("key", [0.1, 0.2])
    assert mem.recall([0.1, 0.2]) == []

# Vector-store interactions are undefined for NullMemory; ensure no errors. 