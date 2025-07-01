from typer.testing import CliRunner

from ice_cli.cli import app


runner = CliRunner()


def test_help_shows_global_flags() -> None:
    """`ice --help` must list the newly added global flags."""

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, result.output

    for flag in ("--json", "--dry-run", "--yes", "--verbose"):
        assert flag in result.output, f"{flag} missing from --help"


def test_global_flags_no_subcommand() -> None:
    """`ice --json` without a sub-command should print help and exit 0."""

    result = runner.invoke(app, ["--json"])

    assert result.exit_code == 0, result.output 