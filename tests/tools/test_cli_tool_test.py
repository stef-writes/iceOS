from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from ice_cli.cli import app

runner = CliRunner()


def _setup_tool(tmp_path: Path):
    code = dedent(
        """
        from __future__ import annotations
        from typing import Any
        from ice_sdk.tools.base import BaseTool, ToolContext

        class EchoTool(BaseTool):
            name = "echo"
            description = "Echo back input"

            async def run(self, ctx: ToolContext, **kwargs: Any):
                return kwargs
        """
    )
    p = tmp_path / "echo.tool.py"
    p.write_text(code)
    # Don't modify sys.path - let the discovery work naturally


def test_cli_tool_test(tmp_path: Path):
    _setup_tool(tmp_path)
    prev = Path.cwd()
    os.chdir(tmp_path)
    try:
        # Clear any cached tool service to force fresh discovery
        from ice_sdk.services import ServiceLocator

        try:
            ServiceLocator.clear()
        except Exception:
            pass

        result = runner.invoke(app, ["tool", "test", "echo", "--args", '{"foo":1}'])
    finally:
        os.chdir(prev)
    assert result.exit_code == 0, result.output
    assert "foo" in result.output
