"""Utility helpers for cheap, deterministic content summarisation.

The *deterministic_summariser* function was originally defined under the
``ice_sdk.tools.builtins.deterministic`` shim.  During the vNext tool
refactor that compatibility layer was removed.  The helper lives on here so
callers (e.g. :pyclass:`ice_sdk.context.manager.GraphContextManager`) can
continue to compress large context payloads without introducing an LLM
dependency.
"""

from __future__ import annotations

from typing import Any, Dict

__all__ = ["deterministic_summariser"]


def deterministic_summariser(
    content: Any,
    *,
    schema: Dict[str, Any] | None = None,  # noqa: D401 – align with GCManager API
    max_tokens: int | None = None,
) -> str:
    """Return a cheap text summary without external dependencies.

    Strategy (v1):
    1. Convert *content* to string (JSON dump for mappings / sequences).
    2. Keep the first ~*max_tokens* tokens (≈4 chars per token) and append an
       ellipsis.

    This is **not** semantic summarisation but provides deterministic
    compression that never calls an LLM – good enough for long-term memory
    where fidelity is less critical than footprint.
    """

    import json

    # Fallback safety ----------------------------------------------------
    try:
        text = (
            content
            if isinstance(content, str)
            else json.dumps(content, ensure_ascii=False, default=str)
        )
    except Exception:  # noqa: BLE001 – best-effort conversion
        text = str(content)

    if max_tokens is None:
        max_tokens = 400

    char_budget = max_tokens * 4  # rough heuristic
    if len(text) <= char_budget:
        return text

    return text[: char_budget - 3] + "…"
