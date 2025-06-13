from __future__ import annotations

from pathlib import Path

from importlinter import cli


def test_import_contracts_pass():
    """Run Import-Linter programmatically and assert zero broken contracts."""
    cfg_path = Path(__file__).resolve().parents[2] / "config/.importlinter"

    exit_code = cli.lint_imports(config_filename=str(cfg_path))

    assert exit_code == 0, "Import-Linter contracts are broken – check the report above." 