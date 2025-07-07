"""DEPRECATED – use `ice doctor all` instead.

This stub exists solely for CI backward-compatibility.
"""

from __future__ import annotations

import subprocess
import sys
import warnings

warnings.warn(
    "`scripts/doctor.py` is deprecated; use `ice doctor all`.  This stub will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> None:  # noqa: D401 – light wrapper
    cmd = [sys.executable, "-m", "ice_cli.cli", "doctor", "all", *sys.argv[1:]]
    subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
