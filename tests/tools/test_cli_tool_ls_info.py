from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from ice_cli.cli import app

runner = CliRunner()


def _make_temp_tool(tmp_path: Path):
    tool_code = dedent(
        """
        from __future__ import annotations
        from typing import Any
        from ice_sdk.tools.base import BaseTool, ToolContext

        class HelloTool(BaseTool):
            name = "hello"
            description = "Say hello"

            async def run(self, ctx: ToolContext, **kwargs: Any):
                return {"hello": "world"}
        """
    )
    tool_path = tmp_path / "hello.tool.py"
    tool_path.write_text(tool_code)
    # Don't modify sys.path - let the discovery work naturally


@pytest.mark.skip("Legacy 'ice tool' commands removed - use 'ice create tool' instead")
@pytest.mark.parametrize("command", [
    "tool ls --refresh",
    "tool info hello",
])
def test_cli_tool_commands(command: str, tmp_path: Path) -> None:
    """Test that legacy tool commands work."""
    _make_temp_tool(tmp_path)
    prev_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        # Clear any cached tool service to force fresh discovery
        from ice_sdk.services import ServiceLocator

        try:
            ServiceLocator.clear()
        except Exception:
            pass

        # Force refresh to ensure the tool is discovered
        if "ls" in command:
            command = command.replace("ls", "ls --refresh")
        result = runner.invoke(app, command.split(), env={"PYTHONPATH": str(tmp_path)})
    finally:
        os.chdir(prev_cwd)
    assert result.exit_code == 0, result.output
    assert "hello" in result.output
