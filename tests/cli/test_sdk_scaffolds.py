from __future__ import annotations

"""Integration tests for the new *ice sdk create-* scaffolds.

These tests use Typer's *CliRunner* to invoke the CLI the same way a user
would on the command-line.  We deliberately execute the generated `*.chain.py`
script to prove that the scaffolded artefacts run end-to-end without manual
edits.
"""

import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from ice_cli.cli import app


def test_create_scaffolds_and_run_chain(tmp_path: Path) -> None:  # noqa: D401
    """Generate tool, node & chain and execute the chain successfully."""

    runner = CliRunner()

    # ------------------------------------------------------------------
    # 1. Create a dummy tool -------------------------------------------
    # ------------------------------------------------------------------
    res = runner.invoke(
        app,
        [
            "sdk",
            "create-tool",
            "FooTool",
            "--dir",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0, res.stdout
    tool_file = tmp_path / "foo_tool.tool.py"
    assert tool_file.exists(), "Tool file not generated"

    # ------------------------------------------------------------------
    # 2. Create an AiNode scaffold -------------------------------------
    # ------------------------------------------------------------------
    res = runner.invoke(
        app,
        [
            "sdk",
            "create-node",
            "BarNode",
            "--type",
            "ai",
            "--dir",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0, res.stdout
    ainode_file = tmp_path / "bar_node.ainode.yaml"
    assert ainode_file.exists(), "AiNode YAML not generated"

    # ------------------------------------------------------------------
    # 3. Create a minimal chain ---------------------------------------
    # ------------------------------------------------------------------
    res = runner.invoke(
        app,
        [
            "sdk",
            "create-chain",
            "hello_chain",
            "--dir",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0, res.stdout
    chain_file = tmp_path / "hello_chain.chain.py"
    assert chain_file.exists(), "Chain file not generated"

    # ------------------------------------------------------------------
    # 4. Execute the generated chain -----------------------------------
    # ------------------------------------------------------------------
    completed = subprocess.run(
        [sys.executable, str(chain_file)], capture_output=True, text=True, check=True
    )
    # Output should contain the echo payload (tool returns {"echo": "hello"})
    assert '"echo": "hello"' in completed.stdout or "'echo': 'hello'" in completed.stdout 