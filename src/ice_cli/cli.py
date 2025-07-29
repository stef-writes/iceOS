"""iceOS command-line interface (pure *Click* implementation).

"""

from __future__ import annotations

"""iceOS command-line interface (pure *Click* implementation).

"""

import subprocess
import sys
from typing import List

import click
import json
from pathlib import Path

import asyncio

# ---------------------------------------------------------------------------
# Async helper ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def _safe_run(coro):  # noqa: ANN001 – generic coroutine
    """Run *coro* regardless of whether an event loop is already running.

    If running inside an existing loop (e.g., Jupyter) we schedule the coroutine
    and block until completion using ``loop.run_until_complete`` after applying
    ``nest_asyncio`` to enable nested loops.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Already inside a loop ---------------------------------------------------
    try:
        import nest_asyncio  # type: ignore

        nest_asyncio.apply()
    except Exception:
        pass  # Optional dependency – if missing we still attempt but may error

    return loop.run_until_complete(coro)

# NOTE: All runtime execution now lives in *ice_orchestrator.cli* to respect
# clean layer boundaries.  We forward commands via *subprocess* instead of
# importing the orchestrator layer directly.

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

# ---------------------------------------------------------------------------
# Network commands -----------------------------------------------------------
# ---------------------------------------------------------------------------


@cli.group()
def network() -> None:
    """Convenience wrapper that forwards to *ice_orchestrator.cli*."""


@network.command("run")
@click.argument("manifest_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--scheduled", is_flag=True, help="Respect cron schedules and watch forever.")
def network_run(manifest_path: str, scheduled: bool) -> None:  # noqa: D401
    """Execute *MANIFEST_PATH* via the runtime CLI without importing it."""

    cmd = [sys.executable, "-m", "ice_orchestrator.cli", "network", "run", manifest_path]
    if scheduled:
        cmd.append("--scheduled")

    subprocess.run(cmd, check=True)

# Alias for Poetry entrypoint -------------------------------------------------
app = cli  # For backward compatibility with pyproject.toml script entry

# Allow "python -m ice_cli.cli ..." invocation ------------------------------
if __name__ == "__main__":  # pragma: no cover
    cli()