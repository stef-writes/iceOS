"""Simple built-in greeting tool used for smoke tests and tutorials."""

from __future__ import annotations

from typing import Any, Dict

from ice_core.base_tool import ToolBase
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry


class HelloTool(ToolBase):
    """Return a friendly greeting.

    Example
    -------
    >>> from ice_core.services import ServiceLocator
    >>> import ice_tools.hello  # noqa: F401 – ensures registration happens
    >>> tool_service = ServiceLocator.get("tool_execution_service")
    >>> result = await tool_service.execute_tool("hello", {"name": "Ada"})
    >>> assert result == {"greeting": "Hello, Ada!"}
    """

    # Metadata required by `ToolBase`
    name: str = "hello"
    description: str = "Return a friendly greeting."

    # ------------------------------------------------------------------
    # Core execution implementation  (rule #2 – all side-effects here)
    # ------------------------------------------------------------------

    async def _execute_impl(self, *, name: str = "world", **_: Any) -> Dict[str, Any]:
        """Generate the greeting.

        Parameters
        ----------
        name:
            Name to greet. Defaults to "world".

        Returns
        -------
        dict[str, str]
            A single-key mapping ``{"greeting": "Hello, <name>!"}``.
        """
        greeting = f"Hello, {name}!"
        return {"greeting": greeting}


# ---------------------------------------------------------------------------
# Auto-registration on import (side-effect limited to registry call)
# ---------------------------------------------------------------------------

_instance = HelloTool()
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
