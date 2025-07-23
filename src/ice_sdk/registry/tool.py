from __future__ import annotations

"""Tool registry – canonical home for deterministic tool implementations.

Wraps the existing *SkillRegistry* but with taxonomy-aligned naming.  Future
code should import *ToolRegistry* / *global_tool_registry*.
"""

import warnings
from typing import Any, Dict, Generator, Mapping, Tuple, Type

from pydantic import BaseModel, PrivateAttr

from ice_sdk.tools.base import SkillBase  # Re-use existing SkillBase until full rename
import importlib.metadata as _metadata

# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "ToolRegistry",
    "global_tool_registry",
]


class ToolRegistrationError(RuntimeError):
    """Raised when a tool cannot be registered in the registry."""


class ToolRegistry(BaseModel):
    """In-memory registry that resolves *Tool* implementations by name.

    Mirrors the former *SkillRegistry* semantics but with taxonomy-aligned
    naming (Rule 1).  Each tool instance **must** inherit from
    :class:`ice_sdk.tools.base.SkillBase` until the project fully migrates to
    a dedicated *ToolBase*.
    """

    # Internal mapping is intentionally excluded from the Pydantic schema
    _tools: Dict[str, SkillBase] = PrivateAttr(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    # ------------------------------------------------------------------ API
    def register(self, name: str, tool: SkillBase) -> None:
        """Register an instantiated *tool* under *name*.

        Parameters
        ----------
        name : str
            Public identifier used by workflows.
        tool : SkillBase
            An instantiated, fully-validated tool (still typed as SkillBase
            for backward compatibility).
        """

        if name in self._tools:
            raise ToolRegistrationError(f"Tool '{name}' already registered")

        # Validation already handled by Pydantic at instantiation
        self._tools[name] = tool

    def get(self, name: str) -> SkillBase:  # noqa: D401 – still returns SkillBase
        """Return the registered *tool* instance identified by *name*."""

        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolRegistrationError(f"Tool '{name}' not found") from exc

    async def execute(self, name: str, payload: Mapping[str, Any]) -> Any:
        """Delegate execution to the named *tool* with *payload*."""

        tool = self.get(name)
        return await tool.execute(dict(payload))

    # ------------------------------------------------------------------ helpers
    def __iter__(self) -> Generator[Tuple[str, SkillBase], None, None]:
        yield from self._tools.items()

    def __len__(self) -> int:  # pragma: no cover – convenience
        return len(self._tools)

    # ------------------------------------------------------------------ entry-point discovery
    def load_entry_points(self, group: str = "iceos.tools") -> int:
        """Discover and register external tools exposed via *entry points*.

        External packages can declare the following in their *pyproject.toml*:

        ```toml
        [tool.poetry.plugins."iceos.tools"]
        "csv-cleaner" = "acme_csv.tools:CsvCleanerTool"
        ```

        On installation (``pip install acme-csv``) the registry loads the
        entry-points, instantiates the classes (if necessary) and registers
        them under the declared name.  Returns the number of successfully
        registered tools so callers can log the outcome.
        """

        try:
            # Python 3.10: entry_points(group=…) → list[EntryPoint]
            eps = _metadata.entry_points(group=group)  # type: ignore[arg-type]
        except TypeError:
            # Older interpreter – use mapping style then select()
            eps = _metadata.entry_points().get(group, [])  # type: ignore[index]

        registered = 0
        for ep in eps:
            try:
                obj = ep.load()
                instance: SkillBase
                if isinstance(obj, type) and issubclass(obj, SkillBase):
                    instance = obj()  # Instantiate with default ctor
                elif isinstance(obj, SkillBase):
                    instance = obj
                else:
                    warnings.warn(
                        f"Entry-point '{ep.name}' did not resolve to SkillBase subclass/instance.",
                        RuntimeWarning,
                    )
                    continue

                name = getattr(instance, "name", ep.name)
                self.register(name, instance)
                registered += 1
            except Exception as exc:  # pylint: disable=broad-except
                warnings.warn(
                    f"Failed to load tool entry-point '{ep.name}': {exc}",
                    RuntimeWarning,
                )
                continue

        return registered


# Global default instance ----------------------------------------------------

global_tool_registry: "ToolRegistry[Any]" = ToolRegistry()  # type: ignore[type-var]

# Attempt to auto-load external tools registered via entry-points.  Errors are
# non-fatal and surfaced as warnings only.
try:
    count_loaded = global_tool_registry.load_entry_points()
    if count_loaded:
        warnings.warn(
            f"Loaded {count_loaded} external tool(s) via entry-points.",
            RuntimeWarning,
            stacklevel=1,
        )
except Exception:  # pragma: no cover – defensive guard
    pass

# Deprecation shim – legacy code may still import *global_skill_registry*
import sys as _sys


_sys.modules.setdefault(
    "ice_sdk.registry.skill",  # type: ignore[arg-type]
    _sys.modules[__name__],
)

# Emit one-time warning so callers migrate – do **not** spam per import
warnings.warn(
    "'global_skill_registry' is deprecated; use 'global_tool_registry' from 'ice_sdk.registry.tool'.",
    DeprecationWarning,
    stacklevel=2,
) 