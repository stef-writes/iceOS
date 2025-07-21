"""CI helper enforcing minimum test coverage.

This script is designed to run *after* ``pytest --cov`` so that the coverage
XML report is available in ``htmlcov`` or the default ``.coverage`` data file.
"""

from __future__ import annotations

import sys

import coverage  # ``pytest-cov`` dependency pulls this in already

MIN_COVERAGE = 60  # Percentage threshold – keep in sync with repo rules


def enforce_coverage() -> None:  # noqa: D401 – CLI helper
    """Exit ``1`` when overall coverage is below *MIN_COVERAGE*."""

    cov = coverage.Coverage()
    cov.load()
    total = cov.report(show_missing=False)  # Returns float percentage

    if total < MIN_COVERAGE:  # pragma: no cover – executed in CI only
        print(
            f"Coverage check failed: {total:.1f}% < required {MIN_COVERAGE}%",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover – executed manually / CI
    enforce_coverage()
