"""Deterministic summarisation helpers (moved from summariser.py)."""

from __future__ import annotations

from typing import Any, Dict

__all__ = ["deterministic_summariser"]


def deterministic_summariser(
    content: Any,
    *,
    schema: Dict[str, Any] | None = None,
    max_tokens: int | None = None,
) -> str:
    import json

    try:
        text = (
            content
            if isinstance(content, str)
            else json.dumps(content, ensure_ascii=False, default=str)
        )
    except Exception:
        text = str(content)
    if max_tokens is None:
        max_tokens = 400
    char_budget = max_tokens * 4
    if len(text) <= char_budget:
        return text
    return text[: char_budget - 3] + "…"
