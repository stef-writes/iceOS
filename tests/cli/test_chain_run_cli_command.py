import json
from pathlib import Path

from typer.testing import CliRunner

from ice_cli.cli import app


def test_cli_chain_run_json(tmp_path: Path) -> None:
    """Running `ice chain run` on the demo chain should succeed and return JSON."""

    runner = CliRunner()

    # Use the relative path to the demo chain included in the repository.
    demo_chain_path = Path("cli_demo/my_chain.chain.py")
    assert demo_chain_path.exists(), "Demo chain file missing – test setup invalid."

    result = runner.invoke(app, ["chain", "run", str(demo_chain_path), "--json"])

    assert result.exit_code == 0, result.stderr

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    # The demo chain has a single node id 'start'
    assert "output" in payload and "start" in payload["output"]
