"""Utility functions for working with toolkits."""

from __future__ import annotations

from typing import Optional

from ice_core.models.enums import NodeType
from ice_core.toolkits.base import BaseToolkit
from ice_core.unified_registry import Registry as _Registry, registry as _global_registry

__all__: list[str] = [
    "register_toolkit",
]


def register_toolkit(
    toolkit: BaseToolkit,
    *,
    namespace: Optional[str] = None,
    validate: bool = True,
    registry: _Registry = _global_registry,
) -> int:
    """Register *all* tools from *toolkit* into *registry*.

    Parameters
    ----------
    toolkit:
        The toolkit instance to register.
    namespace:
        Optional prefix added to each tool's public name.  If omitted the
        toolkit's own ``name`` attribute is used.  Set to an empty string to
        register tools verbatim.
    validate:
        Whether to run ``toolkit.validate()`` before registration.
    registry:
        The target registry.  Defaults to the global singleton but can be
        overridden in tests.

    Returns
    -------
    int
        Number of tools registered.
    """

    from ice_core.unified_registry import Registry as _Registry  # local import for type checking

    if validate:
        toolkit.validate()

    ns: str | None = namespace if namespace is not None else toolkit.name
    count: int = 0

    for tool in toolkit.get_tools():
        # Determine public name: <namespace>.<tool.name> unless namespace is "" or None.
        public_name = f"{ns}.{tool.name}" if ns else tool.name

        # Register instance; reuse registry's built-in validation
        from typing import Any, cast
        registry.register_instance(NodeType.TOOL, public_name, cast(Any, tool))  # type: ignore[arg-type]
        count += 1

    return count
