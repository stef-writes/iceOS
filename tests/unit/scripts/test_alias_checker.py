import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


def test_alias_checker_no_legacy_aliases() -> None:
    """Run the CI alias-checker script and assert it exits with status 0."""

    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "ci" / "check_aliases.py"

    # Execute the checker as a subprocess so we capture its real exit code.
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)

    assert result.returncode == 0, (
        "Legacy node type aliases detected by check_aliases.py:\n" + (result.stderr or result.stdout)
    ) 