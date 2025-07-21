"""Utility helpers for agent-related operations (internal use).

Moved from *ice_sdk.utils.agents.utils* to the dedicated *agents* package.
This module must NOT introduce external side-effects; it only provides pure
helper functions shared by the *ice_sdk.agents* package.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, cast

__all__: list[str] = ["extract_json"]

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.DOTALL)


def extract_json(raw: str) -> Dict[str, Any]:  # noqa: D401 – util name
    """Return ``dict`` parsed from *raw* string.

    The helper tolerates common LLM quirks:
    • Leading/trailing markdown code fences (``` or ```json).
    • Accidental whitespace around the JSON payload.
    """

    if raw.strip().startswith("```"):
        raw = _FENCE_RE.sub("", raw.strip())
    # `json.loads` returns Any; cast to the expected mapping type for callers.
    return cast(Dict[str, Any], json.loads(raw))


# ---------------------------------------------------------------------------
# Outline helpers -----------------------------------------------------------
# ---------------------------------------------------------------------------


def parse_llm_outline(raw: str) -> Dict[str, str]:  # noqa: D401 – util name
    """Return a dict with a single ``outline`` key extracted from *raw*.

    The helper is intentionally *forgiving* because LLMs often deviate from
    strict JSON serialization.  Parsing strategy:

    1. Try :pyfunc:`extract_json` – succeeds when the model returns a
       valid JSON object (optionally wrapped in code fences) and *contains* an
       ``outline`` field.
    2. If step 1 fails – strip code fences and treat the remaining text
       as the outline string.
    """

    # Attempt strict JSON path first -------------------------------------
    try:
        parsed = extract_json(raw)
        if isinstance(parsed, dict) and "outline" in parsed:
            outline_val = parsed["outline"]
            if not isinstance(outline_val, str):
                outline_val = json.dumps(outline_val, ensure_ascii=False)
            return {"outline": outline_val}
    except json.JSONDecodeError:
        pass

    cleaned = _FENCE_RE.sub("", raw).strip()
    return {"outline": cleaned}


# Public re-export -----------------------------------------------------------
__all__.append("parse_llm_outline") 