"""Compatibility shim so tests can import ``ice_cli.main``.

Originally the CLI lives in :pymod:`ice_cli.cli`.  Downstream tests expect
``from ice_cli.main import app`` so we re-export here to preserve that public
surface without creating another entry-point.
"""

from __future__ import annotations

from .cli import app  # re-export

__all__ = ["app"]
