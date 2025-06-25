from __future__ import annotations

import os
import sys
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
    sys.path.insert(0, str(tmp_path))


@pytest.mark.parametrize("cmd", [
    ("tool ls --refresh"), ("tool info hello")])
def test_cli_tool_commands(tmp_path: Path, cmd: str):
    _make_temp_tool(tmp_path)
    prev_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, cmd.split(), env={"PYTHONPATH": str(tmp_path)})
    finally:
        os.chdir(prev_cwd)
    assert result.exit_code == 0, result.output
    assert "hello" in result.output 