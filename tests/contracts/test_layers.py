from __future__ import annotations

import shutil
from pathlib import Path

from importlinter import cli


def test_import_contracts_pass():
    """Run Import-Linter programmatically and assert zero broken contracts."""
    project_root = Path(__file__).resolve().parents[2]
    cfg_path = project_root / "config/.importlinter"

    # Always start with a clean cache to pick up config changes --------------
    cache_dir = project_root / ".import_linter_cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    exit_code = cli.lint_imports(config_filename=str(cfg_path))

    assert (
        exit_code == 0
    ), "Import-Linter contracts are broken – check the report above."
