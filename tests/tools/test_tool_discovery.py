from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

from ice_sdk.tools.service import ToolService


@pytest.mark.asyncio
async def test_discover_and_register(tmp_path: Path):
    """ToolService should discover and register a `*.tool.py` file."""

    # Create dummy tool module -------------------------------------------
    tool_code = dedent(
        """
        from __future__ import annotations
        from typing import Any
        from ice_sdk.tools.base import BaseTool, ToolContext

        class EchoTool(BaseTool):
            name = "echo"
            description = "echoes kwargs"

            async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:
                return kwargs
        """
    )
    tool_path = tmp_path / "echo.tool.py"
    tool_path.write_text(tool_code)

    # Add tmp_path to sys.path so importlib can find it
    sys.path.insert(0, str(tmp_path))

    svc = ToolService(auto_register_builtins=False)
    svc.discover_and_register(tmp_path)

    assert "echo" in svc.available_tools()

    tool_instance = svc.get("echo")
    result = await tool_instance.run(ctx=None, foo="bar")  # type: ignore[arg-type]
    assert result == {"foo": "bar"}
