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
    dry_run: bool = False      # Do not perform mutations – just log intended actions
    yes: bool = False          # Assume *yes* for all confirmation prompts
    verbose: bool = False      # Increase log verbosity
    emit_events: bool = True   # Disable with --no-events


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
    import typer

    if typer_ctx is None:
        # mypy's Typer stubs lack *get_current_context* – silence the false positive.
        typer_ctx = typer.get_current_context()  # type: ignore[assignment,call-arg,attr-defined]

    if getattr(typer_ctx, "obj", None) is None:
        # When a sub-command is invoked directly (e.g. tests) the callback may
        # not have run – create a default context so attribute access is safe.
        setattr(typer_ctx, "obj", CLIContext())

    return getattr(typer_ctx, "obj") 