"""Run the *ice* CLI with ``python -m ice_cli``.

This thin shim simply delegates to :pydata:`ice_cli.cli.app` so users do not
need the Poetry-generated console script when running inside editable clones
or zipped site-packages.
"""

from __future__ import annotations

from .cli import app

if __name__ == "__main__":
    # Typer's .main() helper respects shell completion & exit codes.
    app()
