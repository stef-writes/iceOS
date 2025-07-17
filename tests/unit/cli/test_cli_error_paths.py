from __future__ import annotations

import json
from pathlib import Path

import pytest  # type: ignore
from typer.testing import CliRunner  # type: ignore

from ice_cli.cli import app as ice_app  # type: ignore


def test_unknown_command_exit_code_two():
    runner = CliRunner()
    result = runner.invoke(ice_app, ["unknown"])
    # Typer/Click returns exit code 2 for bad usage
    assert result.exit_code == 2
