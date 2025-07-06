from __future__ import annotations

# ruff: noqa: E402

"""Smoke tests for the new `ice prompt` commands."""

import json
from pathlib import Path

from typer.testing import CliRunner

from ice_cli.cli import app


def test_prompt_create_ls(tmp_path: Path) -> None:  # noqa: D401
    runner = CliRunner()
    # create
    res = runner.invoke(
        app,
        [
            "prompt",
            "create",
            "Demo",
            "--template",
            "Hello {name}",
            "--dir",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0, res.stdout

    # ls should list it
    res = runner.invoke(app, ["prompt", "ls", "--dir", str(tmp_path)])
    assert "Demo" in res.stdout

    # test rendering
    res = runner.invoke(
        app,
        [
            "prompt",
            "test",
            "Demo",
            "--input",
            json.dumps({"name": "Alice"}),
            "--dir",
            str(tmp_path),
        ],
    )
    assert "Hello Alice" in res.stdout
