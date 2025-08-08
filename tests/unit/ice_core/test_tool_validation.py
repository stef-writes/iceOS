from __future__ import annotations

from typing import ClassVar

import pytest

from ice_core.base_tool import ToolBase
from ice_core.exceptions import ValidationError


class DummyTool(ToolBase):
    """Simple tool for validation tests."""

    name: ClassVar[str] = "dummy"
    description: ClassVar[str] = "A dummy validation tool"

    # Declare an *extra* field to test merge behaviour
    some_field: int = 1

    async def _execute_impl(
        self, value: int, optional: str | None = None
    ) -> dict[str, int]:
        return {"result": value * 2}


@pytest.mark.asyncio
async def test_tool_validation_passes():
    tool = DummyTool()
    out = await tool.execute(value=3)
    assert out["result"] == 6


@pytest.mark.asyncio
async def test_tool_validation_fails_on_missing_required():
    tool = DummyTool()
    with pytest.raises(ValidationError):
        await tool.execute()  # type: ignore[arg-type]
