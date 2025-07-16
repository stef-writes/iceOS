from __future__ import annotations

"""`ice models` – list available LLM models.

The command delegates to *ice_core.models.model_registry* so the source of truth
lives in a single place.
"""

import typer
from rich import print as rprint
from rich.table import Table

from ice_core.models.model_registry import list_models

models_app = typer.Typer(add_completion=False, help="LLM model catalog")

__all__ = ["models_app"]


@models_app.command("list", help="Show allowed LLM models and their purpose")
def _list_models() -> None:  # noqa: D401 – CLI entry
    """Render the model registry as a Rich table."""

    table = Table(
        title="Supported LLM Models", show_header=True, header_style="bold magenta"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Provider", style="green")
    table.add_column("Best for", style="yellow")

    for info in list_models():
        table.add_row(info.id, info.provider.value, info.best_for)

    rprint(table)
