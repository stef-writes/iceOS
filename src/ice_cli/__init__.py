"""Command-line interface for iceOS (``ice``).

This package exposes :data:`app` (a *Typer* instance) so it can be used both
via ``python -m ice_cli`` and as an entry-point defined in *pyproject.toml*.
"""

from __future__ import annotations

from .cli import app  # re-export Typer app so entry-point can find it.

__all__ = ["app"]
