import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from ice_cli.cli import app


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
                tool_args={"text": "hello"},
            )
        ]

        chain = ScriptChain(nodes=nodes, tools=[echo_tool], name="demo")
        """
    )

    path = tmp_path / "demo.chain.py"
    path.write_text(source)
    return path


def test_cli_chain_run_json(tmp_path: Path) -> None:
    """Running `ice chain run` on a generated demo chain should succeed and return JSON."""

    chain_file = _create_dummy_chain(tmp_path)

    # Clear global tool registry to avoid cross-test pollution
    from ice_sdk.services import ServiceLocator

    ServiceLocator.clear()

    runner = CliRunner()

    result = runner.invoke(app, ["chain", "run", str(chain_file), "--json"])

    assert result.exit_code == 0, result.stderr

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert "output" in payload and "start" in payload["output"]
