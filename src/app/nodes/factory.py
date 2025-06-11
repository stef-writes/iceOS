"""Dynamic factory that leverages the `ice_sdk` plugin registry first and
falls back to in-tree node implementations for backwards-compatibility."""

from importlib import import_module
from typing import Any

from ice_sdk import get_node_class

# ---------------------------------------------------------------------------
# Legacy, in-tree node classes kept for fallback.  They will be lazily
# imported only if no plugin overrides the node type.
# ---------------------------------------------------------------------------

_LEGACY_NODE_MAP = {
    "ai": "app.nodes.ai.ai_node:AiNode",
    "tool": "app.nodes.tool_node:ToolNode",
}


def node_factory(config: Any, *args, **kwargs):
    """Instantiate a node implementation for *config*.

    Resolution order:
    1. Check `ice_sdk` plugin registry for a node class whose attribute
       ``type`` matches ``config.type``.
    2. Fallback to built-in mapping (`_LEGACY_NODE_MAP`).
    """

    node_cls = get_node_class(config.type)

    if node_cls is None:
        # Fallback to legacy location.
        dotted = _LEGACY_NODE_MAP.get(config.type)
        if not dotted:
            raise ValueError(f"Unknown node type: {config.type}")

        module_name, _, class_name = dotted.partition(":")
        mod = import_module(module_name)
        node_cls = getattr(mod, class_name)

    # ToolNode signature differs slightly – if the node expects a context
    # manager as first positional, preserve legacy behaviour.
    if config.type == "tool":
        # Ensure we don\'t pass duplicate \"context_manager\". Prefer explicit kwarg, fall back to positional.
        if "context_manager" in kwargs:
            context_manager = kwargs.pop("context_manager")
        else:
            context_manager = args[0] if args else None

        return node_cls(config, context_manager=context_manager, **kwargs)

    return node_cls(config, *args, **kwargs)
