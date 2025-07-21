"""iceOS command-line interface (pure *Click* implementation).

The public executable is registered in *pyproject.toml* as::

    [tool.poetry.scripts]
    ice = "ice_cli.cli:cli"

Currently only a **doctor** command is implemented because it is required by
``make doctor`` (and related CI pipelines).  Additional sub-commands can be
added incrementally without breaking existing automation.
"""

from __future__ import annotations

"""iceOS command-line interface (pure *Click* implementation).

The public executable is registered in *pyproject.toml* as::

    [tool.poetry.scripts]
    ice = "ice_cli.cli:cli"

Currently only a **doctor** command is implemented because it is required by
``make doctor`` (and related CI pipelines).  Additional sub-commands can be
added incrementally without breaking existing automation.
"""

import subprocess
import sys
from typing import List

import click

# ---------------------------------------------------------------------------
# Doctor implementation ------------------------------------------------------
# ---------------------------------------------------------------------------

_VALID_TARGETS: dict[str, List[str]] = {
    "lint": ["lint"],
    "type": ["type"],
    "test": ["test"],
    # *all* is expanded into individual targets so we capture granular
    # exit-codes and stop early on first failure.
    "all": ["lint", "type", "test"],
}


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:  # – entrypoint
    """iceOS CLI utilities (run ``ice --help`` for details)."""


@cli.command()
@click.argument(
    "category",
    type=click.Choice(sorted(_VALID_TARGETS.keys()), case_sensitive=False),
    default="all",
    metavar="{lint|type|test|all}",
)
def doctor(category: str) -> None:  # – imperative mood
    """Run repository health-checks (lint, type, test).

    ``CATEGORY`` selects which subset of checks to perform.  The default
    **all** runs *lint*, *type* and *test* sequentially, failing fast on the
    first non-zero exit-status.
    """

    category = category.lower()
    for target in _VALID_TARGETS[category]:
        click.echo(f"[doctor] Running make {target} …")
        completed = subprocess.run(["make", target])
        if completed.returncode != 0:
            click.echo(f"[doctor] make {target} failed", err=True)
            sys.exit(completed.returncode)

    click.echo("[doctor] All checks passed ✔")


# Allow ``python -m ice_cli.cli doctor`` invocation --------------------------
if __name__ == "__main__":  # pragma: no cover
    cli()

# Backward-compat alias expected by older imports (tests, tooling)
app = cli
