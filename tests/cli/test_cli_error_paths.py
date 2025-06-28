import json

import pytest
from typer.testing import CliRunner

from ice_cli.cli import app as ice_app


def test_help_exit_code_zero():
    runner = CliRunner()
    result = runner.invoke(ice_app, ["--help"])
    assert result.exit_code == 0, result.output
    # Ensure some common flag present in help text
    assert "iceOS developer CLI" in result.output


def test_unknown_command_exit_code_two():
    runner = CliRunner()
    result = runner.invoke(ice_app, ["unknown"])
    # Typer/Click returns exit code 2 for bad usage
    assert result.exit_code == 2


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_ls_json_valid_json(monkeypatch):
    """`ice ls --json` must emit valid JSON list."""
    runner = CliRunner()

    # Reduce noise from rich by disabling detection of terminal colors.
    monkeypatch.setenv("PY_COLORS", "0")

    result = runner.invoke(ice_app, ["ls", "--json", "--refresh"])
    assert result.exit_code == 0, result.output
    # Should parse as JSON list of strings
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert all(isinstance(item, str) for item in data) 