"""Deterministic hashing helpers local to *ice_sdk*.

This thin shim exists to preserve the public import path
``ice_sdk.utils.hashing`` which some downstream libraries expect.  Until all
consumers migrate to ``ice_core.utils.hashing`` we simply wrap the core
implementation and expose a convenience ``stable_hash`` helper identical to
Frosty's previous utility.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ice_core.utils.hashing import HashMode, compute_hash  # re-export core helpers

__all__: list[str] = ["stable_hash", "compute_hash", "HashMode"]


def _to_bytes(payload: Any) -> bytes:  # noqa: D401 – helper
    """Serialise *payload* deterministically, falling back to ``repr``.

    We try JSON‐serialisation with ``sort_keys=True`` first so that dictionaries
    with identical key/value pairs but different literal ordering hash to the
    same digest.  Unsupported objects gracefully degrade to their ``repr``.
    """

    try:
        return json.dumps(
            payload, sort_keys=True, default=str, ensure_ascii=False
        ).encode()
    except Exception:  # pragma: no cover – worst-case fallback
        return repr(payload).encode()


def stable_hash(payload: Any) -> str:  # noqa: D401 – public API
    """Return a SHA-256 hash of *payload* suitable for idempotency keys.

    The implementation is **content-based** – any Python object that can be
    serialised to JSON (plus a safe fallback) will produce a deterministic
    hexadecimal digest independent of runtime memory addresses.

    Parameters
    ----------
    payload : Any
        Arbitrary data structure to hash.

    Returns
    -------
    str
        64-character hexadecimal SHA-256 digest.

    Examples
    --------
    >>> stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
    True
    """

    return hashlib.sha256(_to_bytes(payload)).hexdigest()
