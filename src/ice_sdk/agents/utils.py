"""Utility helpers for agent-related operations (internal use).

This module must NOT introduce external side-effects; it only provides pure
helper functions shared by the *ice_sdk.agents* package.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

__all__: list[str] = ["extract_json"]

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.DOTALL)


def extract_json(raw: str) -> Dict[str, Any]:  # noqa: D401 – util name
    """Return ``dict`` parsed from *raw* string.

    The helper tolerates common LLM quirks:
    • Leading/trailing markdown code fences (``` or ```json).
    • Accidental whitespace around the JSON payload.

    Raises
    ------
    json.JSONDecodeError
        When the cleaned text is not valid JSON.
    """

    if raw.strip().startswith("```"):
        raw = _FENCE_RE.sub("", raw.strip())
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Outline helpers -----------------------------------------------------------
# ---------------------------------------------------------------------------


def parse_llm_outline(raw: str) -> Dict[str, str]:  # noqa: D401 – util name
    """Return a dict with a single ``outline`` key extracted from *raw*.

    The helper is intentionally *forgiving* because LLMs often deviate from
    strict JSON serialization.  Parsing strategy:

    1. Try :pyfunc:`extract_json` – this succeeds when the model returns a
       valid JSON object (optionally wrapped in code fences) and *contains* an
       ``outline`` field.
    2. If step 1 fails (syntax error *or* missing key) – strip common Markdown
       code fences / language hints and treat the remaining text as the
       outline string.

    Parameters
    ----------
    raw
        Original LLM response (may include Markdown, code fences, etc.).

    Returns
    -------
    dict
        {"outline": str} mapping that is *always* valid JSON-serialisable.
    """

    # Attempt strict JSON path first -------------------------------------
    try:
        parsed = extract_json(raw)
        if isinstance(parsed, dict) and "outline" in parsed:
            # Ensure value is str – coarse coercion for robustness
            outline_val = parsed["outline"]
            if not isinstance(outline_val, str):
                outline_val = json.dumps(outline_val, ensure_ascii=False)
            return {"outline": outline_val}
    except json.JSONDecodeError:
        # Fall through to lax parsing -----------------------------------
        pass

    # Fallback – remove code fences then return as plain string ----------
    cleaned = _FENCE_RE.sub("", raw).strip()
    return {"outline": cleaned}


# Public re-export -----------------------------------------------------------
__all__.append("parse_llm_outline")
