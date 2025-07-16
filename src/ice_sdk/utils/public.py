"""Shim module re-exporting :pyfunc:`ice_core.utils.meta.public`.

The original implementation used to live here but was migrated to
``ice_core.utils.meta`` in v0.5.  Some downstream tests & user code still
import the legacy path, so we provide a *thin re-export* to avoid breaking
changes until the next major version.
"""

from __future__ import annotations

from ice_core.utils.meta import public  # noqa: F401

__all__: list[str] = ["public"]
