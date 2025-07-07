from __future__ import annotations

import importlib
import sys
import warnings


def test_iceos_meta_package_emits_deprecation_warning():
    """Importing *iceos* should raise a *DeprecationWarning*."""

    # Ensure a fresh import even when the test runner reused the interpreter.
    sys.modules.pop("iceos", None)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always", DeprecationWarning)
        importlib.import_module("iceos")

    assert any(
        isinstance(r.message, DeprecationWarning) for r in records
    ), "Importing 'iceos' did not raise a DeprecationWarning as expected"
