from __future__ import annotations

"""ice_orchestrator CLI – runtime-only commands.

This module is intentionally separate from *ice_cli* to respect the repo's
layer boundaries: anything that actually touches the runtime engine belongs in
this layer.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click

from ice_orchestrator import initialize_orchestrator
from ice_orchestrator.services.network_coordinator import NetworkCoordinator

# ---------------------------------------------------------------------------
# Async helper (copied from ice_cli but kept local to avoid cross-imports) ----
# ---------------------------------------------------------------------------

def _safe_run(coro: Any) -> Any:  # noqa: ANN001 – generic coroutine
    """Run *coro* regardless of whether an event loop is already running."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Inside an existing loop – enable nesting
    try:
        import nest_asyncio  # type: ignore

        nest_asyncio.apply()
    except Exception:  # pragma: no cover – optional dependency
        pass

    return loop.run_until_complete(coro)

# ---------------------------------------------------------------------------
# Top-level group ------------------------------------------------------------
# ---------------------------------------------------------------------------

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Runtime-level commands (execute validated manifests)."""

# ---------------------------------------------------------------------------
# Network manifest commands --------------------------------------------------
# ---------------------------------------------------------------------------

@cli.group()
def network() -> None:
    """Operations for network manifests (multi-workflow execution)."""


@network.command("run")
@click.argument("manifest_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--scheduled", is_flag=True, help="Respect cron schedules and watch forever.")
def network_run(manifest_path: str, scheduled: bool) -> None:  # noqa: D401
    """Execute workflows defined in *MANIFEST_PATH*."""

    initialize_orchestrator()

    coordinator = NetworkCoordinator.from_file(Path(manifest_path))

    if scheduled:
        click.echo(f"[network] Watching schedules in {manifest_path} (Ctrl+C to stop)…")

        async def _run_forever() -> None:
            await coordinator.execute_scheduled(loop_forever=True)

        try:
            _safe_run(_run_forever())
        except KeyboardInterrupt:
            click.echo("[network] Terminated by user.")
            sys.exit(130)
    else:
        results = coordinator.run()
        click.echo("[network] Execution completed – results summary:")
        click.echo(json.dumps({k: getattr(v, "success", None) for k, v in results.items()}, indent=2))


# ---------------------------------------------------------------------------
# Entry-point ----------------------------------------------------------------
# ---------------------------------------------------------------------------

# Allow `python -m ice_orchestrator.cli ...` invocation
if __name__ == "__main__":  # pragma: no cover
    cli() 