import pytest
from typer.testing import CliRunner  # type: ignore

from ice_cli.cli import app  # type: ignore


@pytest.mark.asyncio
def test_models_list_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["models", "list"])
    assert result.exit_code == 0, result.stdout

    output = result.stdout.lower()
    # Expected allowed model appears
    assert "gpt-4o" in output
    # Forbidden model must not appear
    assert "gpt-3.5" not in output
