"""Standalone PgVectorStore stub for contract tests."""

from __future__ import annotations

from . import PgVectorStore  # re-export

# Export symbol to satisfy linter unused import
__all__: list[str] = ["PgVectorStore"]
