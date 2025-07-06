from __future__ import annotations

# ruff: noqa: E402

"""`ice edit` – open nodes or tools in $EDITOR quickly.

Designed for rapid tweaks during iterative chain development.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

edit_app = typer.Typer(help="Open configuration files in your $EDITOR.")

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _open_in_editor(path: Path) -> None:  # noqa: D401 – helper
    """Launch the user's preferred `$EDITOR` synchronously."""

    editor = os.environ.get("EDITOR", "vi")
    try:
        subprocess.run([editor, str(path)], check=True)
    except FileNotFoundError:
        rprint(f"[red]Error:[/] Editor '{editor}' not found. Set $EDITOR.")
        raise typer.Exit(1)
    except subprocess.CalledProcessError as exc:
        rprint(f"[red]Editor exited with non-zero status:[/] {exc.returncode}")
        raise typer.Exit(exc.returncode)


# ---------------------------------------------------------------------------
# `edit node` ----------------------------------------------------------------
# ---------------------------------------------------------------------------


@edit_app.command("node", help="Open a *.ainode.yaml file for editing")
def edit_node(
    name: str = typer.Argument(..., help="Node ID or filename without extension"),
    directory: Optional[Path] = typer.Option(
        None,
        "--dir",
        "-d",
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        help="Directory containing node YAMLs (defaults to ./nodes)",
    ),
):
    if directory is None:
        directory = Path.cwd() / "nodes"
    target = directory / f"{name}.ainode.yaml"
    if not target.exists():
        rprint(f"[red]Error:[/] {target} not found.")
        raise typer.Exit(1)

    _open_in_editor(target)


# ---------------------------------------------------------------------------
# `edit tool` ----------------------------------------------------------------
# ---------------------------------------------------------------------------


@edit_app.command("tool", help="Open a *.tool.py file for editing")
def edit_tool(
    name: str = typer.Argument(..., help="Tool name (snake_case without .tool.py)"),
    directory: Optional[Path] = typer.Option(
        None,
        "--dir",
        "-d",
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        help="Directory containing tool modules (defaults to ./tools)",
    ),
):
    if directory is None:
        directory = Path.cwd() / "tools"
    target = directory / f"{name}.tool.py"
    if not target.exists():
        rprint(f"[red]Error:[/] {target} not found.")
        raise typer.Exit(1)

    _open_in_editor(target)
