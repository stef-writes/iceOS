from __future__ import annotations

"""`ice space` – workspace-level helpers.

A *space* is just a directory with a `chains.toml` manifest plus a few
conventional sub-folders.  This module was extracted from the old monolithic
CLI so the root file remains lightweight.
"""

import shutil
from pathlib import Path

import typer
from rich import print as rprint

space_app = typer.Typer(
    add_completion=False, help="Manage iceOS workspaces (aka 'spaces')"
)

__all__ = ["space_app"]


@space_app.command(
    "create", help="Create a new workspace directory and initialise defaults"
)
def space_create(  # noqa: D401 – simple CLI wrapper
    name: str = typer.Argument(..., help="Directory name for the new space"),
    directory: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        dir_okay=True,
        file_okay=False,
        exists=True,
        writable=True,
        help="Parent directory in which to create the space",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite if directory already exists"
    ),
):
    """Scaffold *name*/ with a starter `chains.toml`."""

    dest = directory / name
    if dest.exists():
        if not force:
            rprint(
                f"[red]✗ Directory '{dest}' already exists – use --force to overwrite.[/]"
            )
            raise typer.Exit(code=1)
        shutil.rmtree(dest)

    dest.mkdir(parents=True, exist_ok=True)
    (dest / "chains.toml").write_text("# iceOS chains manifest\n\n")
    rprint(f"[green]✔[/] Created space at {dest}")
