import pytest

from ice_sdk.tools.base import function_tool


@function_tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@pytest.mark.asyncio
async def test_function_tool_decorator_simple():
    """The generated tool instance should execute and expose metadata."""

    # Execute tool
    result = await add.run(a=2, b=3)
    assert result == 5

    # Verify metadata dict is well-formed
    meta = add.as_dict()
    assert meta["name"] == "add"
    assert "parameters" in meta and "a" in meta["parameters"]
