"""iceOS CLI package. Contains Typer/Click commands and core helpers."""

__all__: list[str] = ["app"]

from .cli import app  # re-export for `python -m ice_cli.cli` convenience
