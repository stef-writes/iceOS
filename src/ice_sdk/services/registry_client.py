"""Developer-facing facade around the canonical `ice_core.unified_registry`.

This helper lives in the *SDK* layer so external developers don’t have to know
about :pymod:`ice_core.unified_registry` internals or the `NodeType` enum.
It exposes symmetrical convenience methods for **all** first-class node types
while delegating every call to the single source-of-truth registry instance in
``ice_core``.

Nothing is stored here – the class is just sugar.  All state remains in
``ice_core.unified_registry.registry`` so architectural purity (Rule 4) is
preserved.
"""

from __future__ import annotations

import inspect
from typing import Any, List, Optional, Type

from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry  # canonical, stateful instance

__all__ = [
    "RegistryClient",
]


class RegistryClient:  # noqa: D101 – public helper
    """Thin convenience wrapper over the unified registry.

    Example
    -------
    >>> rc = RegistryClient()
    >>> rc.register(NodeType.TOOL, "my_tool", MyToolClass)
    >>> tools = rc.list(NodeType.TOOL)
    >>> tool_cls = rc.get_class(NodeType.TOOL, "my_tool")
    """

    # ---------------------------------------------------------------------
    # Generic helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def register(node_type: NodeType, name: str, obj: Any, *, force: bool = False) -> None:  # noqa: D401
        """Register *obj* under *name* for the given *node_type*.

        If *obj* is a class, it is stored via ``register_class``; otherwise it
        is treated as a singleton instance.  This mirrors the public registry
        API but removes the need for callers to decide which method to use.
        """
        if inspect.isclass(obj):
            registry.register_class(node_type, name, obj) if not force else registry.register_class(node_type, name, obj)  # type: ignore[arg-type]
        else:
            registry.register_instance(node_type, name, obj) if not force else registry.register_instance(node_type, name, obj)  # type: ignore[arg-type]

    # Explicit class / instance helpers – occasionally useful --------------
    @staticmethod
    def register_class(node_type: NodeType, name: str, cls: Type[Any]) -> None:
        registry.register_class(node_type, name, cls)

    @staticmethod
    def register_instance(node_type: NodeType, name: str, instance: Any) -> None:
        registry.register_instance(node_type, name, instance)

    # Retrieval helpers ----------------------------------------------------
    @staticmethod
    def get_class(node_type: NodeType, name: str) -> Optional[Type[Any]]:
        try:
            return registry.get_class(node_type, name)
        except Exception:  # noqa: BLE001 – return None on not-found
            return None

    @staticmethod
    def get_instance(node_type: NodeType, name: str) -> Optional[Any]:
        try:
            return registry.get_instance(node_type, name)
        except Exception:  # noqa: BLE001 – return None on not-found / not-registered
            return None

    # Listing helpers ------------------------------------------------------
    @staticmethod
    def list(node_type: NodeType) -> List[str]:
        """Return all component names for *node_type*."""
        return [n for _t, n in registry.list_nodes(node_type)]

    # Convenience wrappers per common node type ---------------------------
    def list_tools(self) -> List[str]:
        return self.list(NodeType.TOOL)

    def list_agents(self) -> List[str]:
        return self.list(NodeType.AGENT)

    def list_workflows(self) -> List[str]:
        return self.list(NodeType.WORKFLOW)

    # etc. – callers can still use the generic *list()* method for other types 