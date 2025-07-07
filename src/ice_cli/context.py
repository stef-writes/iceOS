from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CLIContext:
    """Global options shared across *ice* sub-commands.

    The object is attached to Typer's :class:`typer.Context.obj` so every
    sub-command can read the user's global flags without redefining them.
    """

    json_output: bool = False  # Default to machine-readable JSON instead of Rich tables
    dry_run: bool = False  # Do not perform mutations – just log intended actions
    yes: bool = False  # Assume *yes* for all confirmation prompts
    verbose: bool = False  # Increase log verbosity
    emit_events: bool = True  # Disable with --no-events


# ---------------------------------------------------------------------------
# Helper – convenience accessor inside sub-commands
# ---------------------------------------------------------------------------


def get_ctx(typer_ctx: Any | None = None) -> CLIContext:  # noqa: D401 – helper name
    """Return the :class:`CLIContext` stored in *typer_ctx* or the current one.

    Usage::

        import typer
        from ice_cli.context import get_ctx

        def some_cmd():
            ctx = get_ctx()
            if ctx.dry_run:
                ...
    """

    # Late import to avoid hard dependency for modules that do not use Typer.
    import click
    import typer

    # ------------------------------------------------------------------
    # Typer ≥0.12 removed the top-level ``get_current_context`` helper.
    # Provide a graceful fallback that proxies to Click so older code
    # paths continue to work irrespective of the installed Typer version.
    # ------------------------------------------------------------------
    if not hasattr(typer, "get_current_context"):  # pragma: no cover
        # Expose a shim with the same name + signature.
        def _typer_get_current_context() -> click.Context:  # type: ignore[override]  # pragma: no cover
            return (
                click.get_current_context()
            )  # noqa: WPS437 – re-export helper  # pragma: no cover

        typer.get_current_context = _typer_get_current_context  # type: ignore[attr-defined]  # pragma: no cover

    if typer_ctx is None:
        # NOTE: The shim above ensures ``typer.get_current_context`` exists
        # regardless of the Typer version installed.
        typer_ctx = typer.get_current_context()  # type: ignore[assignment,call-arg,attr-defined]

    if getattr(typer_ctx, "obj", None) is None:
        # When a sub-command is invoked directly (e.g. tests) the callback may
        # not have run – create a default context so attribute access is safe.
        setattr(typer_ctx, "obj", CLIContext())

    return getattr(typer_ctx, "obj")


def validate_layer_boundaries() -> None:  # noqa: D401 – helper
    """Raise ``ImportError`` if demo code crosses forbidden layer boundaries.

    Design rule (#4 in repo rules): demo packages under ``cli_demo.*`` must not
    import from ``ice_sdk.*`` directly.  This lightweight runtime guard can be
    invoked at the top of demo entry-points to ensure boundaries remain intact
    even when linters or import-linter are mis-configured.
    """

    import sys

    for module_name in sys.modules:
        if module_name.startswith("cli_demo.") and ".ice_sdk" in module_name:
            raise ImportError(
                "Demo packages may not import internal SDK modules (layer boundary violation).",
            )
