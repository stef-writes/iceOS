"""Base class for *toolkits* – coherent bundles of tools.

A *toolkit* groups several :class:`ice_core.base_tool.ToolBase` implementations
under a common configuration (e.g. GitHub credentials, SQL DSN, Gmail OAuth
scopes).  It is **not** a runtime node; instead it is a convenience factory that
returns fully-validated tool instances ready for registration with the
:pyclass:`ice_core.unified_registry.Registry`.

The class deliberately stays minimal so that individual toolkits can extend it
without breaking iceOS layer boundaries.

Design goals
------------
1.  **Idempotent validation** (`validate`) – required by iceOS rule #13.
2.  **Async-friendly shutdown** (`shutdown`) – for pooled DB or HTTP clients.
3.  **Declarative dependency list** (`dependencies`) – used by installers / CI
    to install optional extras defined in *pyproject.toml*.
4.  **Strict typing** – full mypy `--strict` compatibility.
"""

from __future__ import annotations

import abc
from typing import List

from pydantic import BaseModel, ConfigDict

from ice_core.base_tool import ToolBase

__all__: list[str] = [
    "BaseToolkit",
]


class BaseToolkit(BaseModel, abc.ABC):
    """Abstract base class for all toolkits."""

    # ---------------------------------------------------------------------
    # Pydantic config
    # ---------------------------------------------------------------------

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # ------------------------------------------------------------------
    # Required attributes / methods – subclasses **must** override
    # ------------------------------------------------------------------

    name: str  # dotted identifier, e.g. "github" or "sql"

    @classmethod
    @abc.abstractmethod
    def dependencies(cls) -> List[str]:
        """Return a list of runtime dependency specifiers.

        Example::

            return ["PyGithub>=2.3.0"]
        """

    @abc.abstractmethod
    def get_tools(self, *, include_extras: bool = False) -> List[ToolBase]:
        """Instantiate and return all tools bundled in this toolkit.

        The method **must** create *new* tool instances on every call so that
        callers can register each toolkit multiple times with different
        configurations.

        Parameters
        ----------
        include_extras:
            If *True* the toolkit may include tools that are disabled by default
            because they incur heavy dependencies or API costs (mirrors
            LangChain's `include_release_tools=True`).
        """

    # ------------------------------------------------------------------
    # Optional hooks
    # ------------------------------------------------------------------

    def validate(self) -> None:  # type: ignore[override]  # noqa: D401 – simple imperative verb is OK
        """Idempotent validation hook.

        Subclasses should raise a **typed**, domain-specific exception if the
        configuration is invalid (rule #9).  The default implementation does
        nothing.
        """

    async def shutdown(self) -> None:  # noqa: D401
        """Async cleanup hook (close DB pools, HTTP clients, etc.)."""

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def register(self, *, namespace: str | None = None) -> int:  # pragma: no cover
        """Register all toolkit tools with the *global* registry.

        This is a thin wrapper around
        :func:`ice_core.toolkits.utils.register_toolkit` to allow::

            GitHubToolkit(...).register()
        """

        from ice_core.toolkits.utils import register_toolkit  # local import to avoid cycles

        return register_toolkit(self, namespace=namespace)
