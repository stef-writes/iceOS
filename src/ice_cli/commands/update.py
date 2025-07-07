from __future__ import annotations

"""`ice update` – misc maintenance helpers (placeholder)."""

import typer
from rich import print as rprint

update_app = typer.Typer(add_completion=False, help="Self-update helpers")

__all__ = ["update_app"]


@update_app.command("templates")
def update_templates():
    """Fetch latest templates (TODO)."""

    rprint("[yellow]TODO:[/] Download latest templates from remote repo.")
