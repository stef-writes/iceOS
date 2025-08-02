"""Simple built-in greeting tool used for smoke tests and tutorials."""

from __future__ import annotations

from typing import Any, Dict

from ice_builder.dsl.decorators import tool
from ice_core.base_tool import ToolBase


@tool(name="hello")
class HelloTool(ToolBase):
    """Return a friendly greeting.

    Example
    -------
    >>> from ice_tools.hello import HelloTool  # noqa: F401 – auto-registers via decorator
    >>> # Using ToolExecutionService (pseudo-code):
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
