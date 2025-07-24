"""Utility helpers for deterministic hashing of content.

Default mode is SHA-256 for security/audit trails.  Additional modes can be
opted into for performance (BLAKE3) or semantic duplicate detection
(MinHash).  BLAKE3 and MinHash are **optional** dependencies – if missing, the
utility gracefully falls back to SHA-256.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Callable, cast

try:  # Optional – used only in PERFORMANCE mode
    import blake3  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional dep
    blake3 = None  # type: ignore

try:
    from datasketch import MinHash  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional dep
    MinHash = None  # type: ignore

__all__: list[str] = ["HashMode", "compute_hash"]

class HashMode(str, Enum):
    """Supported hashing strategies."""

    SECURITY = "sha256"  # Cryptographic auditability
    PERFORMANCE = "blake3"  # Fast but non-crypto
    SEMANTIC = "minhash"  # Near-duplicate detection (not yet implemented)

def _sha256(data: bytes) -> str:  # – helper
    return hashlib.sha256(data).hexdigest()

def _blake3(data: bytes) -> str:  # – helper
    if blake3 is None:  # pragma: no cover – optional dep
        return _sha256(data)
    return cast(str, blake3.blake3(data).hexdigest())  # type: ignore[attr-defined]

_HASH_IMPL: dict[HashMode, Callable[[bytes], str]] = {
    HashMode.SECURITY: _sha256,
    HashMode.PERFORMANCE: _blake3,
}

def _minhash_sig(text: str) -> str:  # – helper
    if MinHash is None:  # pragma: no cover – optional dep
        return _sha256(text.encode())

    m = MinHash(num_perm=64)
    for token in text.split():
        m.update(token.encode())
    return cast(str, m.digest().hex())

def compute_hash(content: str, mode: HashMode = HashMode.SECURITY) -> str:
    """Return hexadecimal hash digest of *content* using *mode*."""
    if mode is HashMode.SEMANTIC:
        return _minhash_sig(content)

    if mode is HashMode.PERFORMANCE:
        return _blake3(content.encode())

    return _sha256(content.encode())
