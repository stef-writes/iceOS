"""Utility functions for working with toolkits."""

from __future__ import annotations

from typing import Optional

from ice_core.toolkits.base import BaseToolkit
from ice_core.unified_registry import Registry as _Registry
from ice_core.unified_registry import registry as _global_registry

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

    if validate:
        toolkit.validate()

    ns: str | None = namespace if namespace is not None else toolkit.name
    count: int = 0

    for tool in toolkit.get_tools():
        # Determine public name: <namespace>.<tool.name> unless namespace is "" or None.
        public_name = f"{ns}.{tool.name}" if ns else tool.name

        # Expect each tool class to expose a module-level factory named create_<name>
        module_path = tool.__class__.__module__
        factory_name = f"create_{tool.name}"
        import_path = f"{module_path}:{factory_name}"

        # Prefer explicit factory if present; otherwise register class as factory
        try:
            import importlib

            mod = importlib.import_module(module_path)
            if not hasattr(mod, factory_name):
                import_path = f"{module_path}:{tool.__class__.__name__}"
        except Exception:
            # If we cannot import the module here, defer to registry and let it raise
            pass

        registry.register_tool_factory(public_name, import_path)
        count += 1

    return count
