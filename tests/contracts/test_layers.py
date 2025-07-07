from __future__ import annotations

import shutil
from pathlib import Path

# Skip if dependency unavailable (CI environments without dev extras)
import pytest  # type: ignore

importlinter_cli = pytest.importorskip("importlinter.cli", reason="importlinter not installed")

# Purposely import lazily after the skip check
from importlinter import cli as _cli  # type: ignore


def test_import_contracts_pass():
    """Run Import-Linter programmatically and assert zero broken contracts."""
    project_root = Path(__file__).resolve().parents[2]
    cfg_path = project_root / "config/.importlinter"

    # Always start with a clean cache to pick up config changes --------------
    cache_dir = project_root / ".import_linter_cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    # Use resolved CLI
    exit_code = _cli.lint_imports(config_filename=str(cfg_path))

    assert (
        exit_code == 0
    ), "Import-Linter contracts are broken – check the report above."
