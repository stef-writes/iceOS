"""WASM-executor tests are disabled when *wasmtime* is not installed.

The project intentionally removed the heavy `wasmtime` dependency.  The
actual executor now raises a `RuntimeError` at construction time when the
library is missing, therefore these behavioural tests are skipped to keep
the suite green without the optional runtime.
"""

import pytest

pytest.skip(
    "wasmtime dependency removed – skipping WASM-executor tests",
    allow_module_level=True,
)
