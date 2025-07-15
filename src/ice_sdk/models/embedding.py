"""Simple Embedding data model (stub)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

DEFAULT_DIM: int = 1536  # matches OpenAI ada-002


@dataclass(slots=True)
class Embedding:
    """Vector embedding wrapper used in tests."""

    vector: List[float]
    model_version: str = "test-model"
