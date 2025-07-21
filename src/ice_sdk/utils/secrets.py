"""Secret management stubs used exclusively in the test-suite.

This module exists so that `tests/conftest.py` can monkey-patch
`ice_sdk.utils.secrets.get_secret` without importing an external
secret-manager at runtime.  Production code SHOULD replace this with a
proper implementation.
"""

from __future__ import annotations

from typing import Final

__all__: Final = ["get_secret"]


def get_secret(key: str) -> str | None:  # noqa: D401 – simple helper
    """Return ``None`` for every key.

    The project’s test-suite monkey-patches this function to avoid network
    calls.  Shipping a no-op default prevents *ImportError* while keeping a
    clear extension point for future secret backends.

    Parameters
    ----------
    key: str
        Secret identifier requested by calling code.

    Returns
    -------
    str | None
        Always ``None`` in the stub implementation.
    """

    return None
