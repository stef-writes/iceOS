"""Unit tests for toolkit registration helper."""

from __future__ import annotations

import pytest

from ice_core.base_tool import ToolBase
from ice_core.toolkits.base import BaseToolkit
from ice_core.toolkits.utils import register_toolkit
from ice_core.unified_registry import Registry


class _DummyTool(ToolBase):
    """Minimal tool implementation used for testing."""

    name: str = "dummy"
    description: str = "A dummy testing tool."

    async def _execute_impl(self, *, echo: str) -> dict[str, str]:  # noqa: D401
        return {"echo": echo}


class _DummyToolkit(BaseToolkit):
    name: str = "dummy"

    token: str = "abc123"  # example field to ensure pydantic validation works

    @classmethod
    def dependencies(cls) -> list[str]:  # noqa: D401
        return ["some-lib>=1.0"]

    def get_tools(self, *, include_extras: bool = False):  # noqa: D401
        # Ignore include_extras for this simple test
        return [_DummyTool()]

    def validate(self) -> None:  # noqa: D401 – override to include basic check
        if not self.token:
            raise ValueError("token must not be empty")


@pytest.mark.asyncio()
async def test_register_toolkit_creates_tools():
    registry = Registry()
    tk = _DummyToolkit(token="secret")

    num = register_toolkit(tk, registry=registry, validate=True)
    assert num == 1, "Exactly one tool should be registered"

    assert registry.has_tool(
        "dummy.dummy"
    ), "Tool should be registered with namespace prefix"

    # Execute the tool to ensure it works end-to-end
    tool = registry.get_tool("dummy.dummy")
    result = await tool.execute(echo="hello")
    assert result == {"echo": "hello"}
