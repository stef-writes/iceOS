from __future__ import annotations

# ruff: noqa: E402

"""Basic smoke tests for the new `ice chain` sub-commands."""

import os
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from ice_cli.cli import app


def test_chain_help() -> None:  # noqa: D401 – simple smoke test
    runner = CliRunner()
    res = runner.invoke(app, ["chain", "--help"])
    assert res.exit_code == 0, res.stdout
    # Ensure a couple of expected sub-commands show up
    assert "create" in res.stdout
    assert "run" in res.stdout


def _create_dummy_chain(tmp_path: Path) -> Path:
    """Return path to a minimal valid chain file written to *tmp_path*."""

    source = dedent(
        """
        from __future__ import annotations

        from typing import Any, List

        from ice_orchestrator.script_chain import ScriptChain
        from ice_sdk.models.node_models import ToolNodeConfig
        from ice_sdk.tools.base import function_tool, ToolContext


        @function_tool(name_override="echo")
        async def _echo(ctx: ToolContext, text: str) -> dict[str, Any]:  # type: ignore[override]
            return {"echo": text}


        echo_tool = _echo

        nodes: List[ToolNodeConfig] = [
            ToolNodeConfig(
                id="start",
                type="tool",
                name="echo_start",
                tool_name="echo",
                tool_args={"text": "hi"},
            )
        ]

        def get_chain():
            return ScriptChain(nodes=nodes, tools=[echo_tool], name="demo")
        """
    )

    path = tmp_path / "demo.chain.py"
    path.write_text(source)
    return path


def test_chain_validate_demo(tmp_path: Path) -> None:  # noqa: D401 – integration
    chain_file = _create_dummy_chain(tmp_path)

    runner = CliRunner()

    # Clear ServiceLocator to avoid stale state between tests
    from ice_sdk.services import ServiceLocator

    ServiceLocator.clear()

    prev_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        res = runner.invoke(app, ["chain", "validate", str(chain_file)])
    finally:
        os.chdir(prev_cwd)

    assert res.exit_code == 0, res.stdout
