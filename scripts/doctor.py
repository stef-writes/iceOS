"""Comprehensive health-check runner for the iceOS repo.

Usage
-----
$ python scripts/doctor.py            # run all checks
$ python scripts/doctor.py --perf     # include performance smoke tests

It mirrors the list in HEALTHCHECKS.md. Each check returning a non-zero exit
status is considered *failure* and aborts the run (unless --keep-going is set).
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Check:
    label: str
    command: str
    perf_only: bool = False  # Run only if --perf flag is set

    def run(self) -> int:
        """Execute the check returning the exit code."""

        print(f"\n▶ {self.label}\n$ {self.command}")
        result = subprocess.run(
            shlex.split(self.command),
            cwd=REPO_ROOT,
            capture_output=False,
        )
        if result.returncode == 0:
            print("✅ PASSED")
        else:
            print(f"❌ FAILED (exit={result.returncode})")
        return result.returncode


# ---------------------------------------------------------------------------
# Check registry
# ---------------------------------------------------------------------------

CHECKS: List[Check] = [
    Check("Linting (ruff)", "ruff src"),
    Check("Typing (pyright)", "pyright --project config"),
    Check("Unit & integration tests", "make test -j"),
    Check("Coverage threshold", "pytest --cov=ice_sdk --cov=ice_orchestrator --cov-fail-under=54 -q"),
    Check("Security audit", "pip-audit"),
    Check("Import-linter rules", "lint-imports --config config/.importlinter"),
    Check("isort check", "isort --check-only src"),
    Check("JSON/YAML validity", "python -m scripts.cli.check_json_yaml"),
    Check("Performance smoke", "pytest --benchmark-only -q", perf_only=True),
]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:  # noqa: D401
    parser = argparse.ArgumentParser(description="iceOS doctor – repo healthchecks")
    parser.add_argument(
        "--perf",
        action="store_true",
        help="Include performance heavy checks (benchmarks)",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Run all checks even if previous failed",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: D401 (imperative mood)
    args = parse_args()
    failed = False

    for check in CHECKS:
        if check.perf_only and not args.perf:
            continue
        exit_code = check.run()
        if exit_code != 0:
            failed = True
            if not args.keep_going:
                sys.exit(exit_code)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
