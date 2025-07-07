"""
iceos meta-package
==================
A *convenience wrapper* that bundles the primary iceOS building blocks under a
single import namespace.  Installing `iceos` pulls in the following
sub-packages as dependencies (declared in *pyproject.toml*):

    • `ice_sdk`          – Core abstractions & runtime helpers
    • `ice_orchestrator` – Workflow engine for distributed execution
    • `app`              – Reference application implementation

Importing `iceos` re-exports those modules so they are available as:

```python
import iceos

iceos.sdk           # the `ice_sdk` package
iceos.orchestrator  # the `ice_orchestrator` package
iceos.app           # the `app` package
```

For quick scripts the meta-package also surfaces commonly used classes:

```python
from iceos import BaseNode, BaseTool
```

The module carries **no side-effects** other than importing the underlying
packages; therefore it does not violate the layer boundaries defined in
`ADR` docs (SDK never imports App, etc.).
"""

from __future__ import annotations

import sys
import warnings
from types import ModuleType  # noqa: WPS433 – runtime helper only
from typing import Final

# ---------------------------------------------------------------------------
# Deprecation notice ---------------------------------------------------------
# ---------------------------------------------------------------------------
warnings.warn(
    (
        "The 'iceos' meta-package is deprecated and will be removed in a future "
        "release. Import sub-packages directly (e.g. `import ice_sdk`) instead."
    ),
    DeprecationWarning,
    stacklevel=2,
)

# ---------------------------------------------------------------------------
# Static imports (no dynamic importlib usage) --------------------------------
# ---------------------------------------------------------------------------

# Map canonical upstream package names to the alias under the `iceos` namespace
_PACKAGES: Final[dict[str, str]] = {
    "sdk": "ice_sdk",
    "orchestrator": "ice_orchestrator",
    "app": "app",
}

_imported: dict[str, ModuleType] = {}

# Attempt to import known sub-packages *explicitly* so we avoid dynamic
# importlib.import_module calls. Missing dependencies are silently ignored –
# callers should install the desired package(s) explicitly.

try:
    import ice_sdk as _ice_sdk  # type: ignore  # noqa: WPS433

    _imported["sdk"] = _ice_sdk  # type: ignore[var-annotated]
except ModuleNotFoundError:  # pragma: no cover – optional dep
    pass

try:
    import ice_orchestrator as _ice_orchestrator  # type: ignore  # noqa: WPS433

    _imported["orchestrator"] = _ice_orchestrator  # type: ignore[var-annotated]
except ModuleNotFoundError:  # pragma: no cover
    pass

try:
    import app as _app  # type: ignore  # noqa: WPS433

    _imported["app"] = _app  # type: ignore[var-annotated]
except ModuleNotFoundError:  # pragma: no cover
    pass

# Expose imported modules under the `iceos` namespace ------------------------
for _alias, _module in _imported.items():
    sys.modules[f"{__name__}.{_alias}"] = _module
    globals()[_alias] = _module

# Surface key symbols for convenience, if `ice_sdk` is present
try:
    from ice_sdk.base_node import BaseNode as BaseNode  # type: ignore
    from ice_sdk.tools.base import BaseTool as BaseTool  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional dependency missing
    # Keep placeholders to avoid AttributeError; real code should depend on
    # `ice_sdk` being installed if it needs these classes.
    class _Missing:  # type: ignore
        def __getattr__(self, name: str) -> None:  # noqa: D401
            raise ModuleNotFoundError(
                "ice_sdk not installed – install the full `iceos` bundle or "
                "add `ice_sdk` to your dependencies"
            )

    BaseNode = BaseTool = _Missing()  # type: ignore

# Public API of the meta-package
__all__: Final[list[str]] = [
    "sdk",
    "orchestrator",
    "app",
    "BaseNode",
    "BaseTool",
]

"""iceOS umbrella meta-package.

This meta-package currently re-exports the public symbols of the
main runtime packages so that third-party code can simply do::

    import iceos
    iceos.ScriptChain(...)

without caring about the deeper layout under ``src/``.

It deliberately keeps **zero** business logic – only lightweight imports – so
it doesn't create dependency inversions (Cursor rule #4).
"""

__version__ = "0.1.0"
