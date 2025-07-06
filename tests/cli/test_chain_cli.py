from __future__ import annotations

# ruff: noqa: E402

"""Basic smoke tests for the new `ice chain` sub-commands."""

from pathlib import Path

from typer.testing import CliRunner

from ice_cli.cli import app


def test_chain_help() -> None:  # noqa: D401 – simple smoke test
    runner = CliRunner()
    res = runner.invoke(app, ["chain", "--help"])
    assert res.exit_code == 0, res.stdout
    # Ensure a couple of expected sub-commands show up
    assert "create" in res.stdout
    assert "run" in res.stdout


# Use an existing demo chain to validate ------------------------------------
_DEMO_CHAIN = (
    Path(__file__).resolve().parent.parent.parent
    / "demos"
    / "essay_writer"
    / "essay_chain.chain.py"
)


def test_chain_validate_demo() -> None:  # noqa: D401 – integration
    runner = CliRunner()
    res = runner.invoke(app, ["chain", "validate", str(_DEMO_CHAIN)])
    assert res.exit_code == 0, res.stdout
