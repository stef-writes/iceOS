"""Builtin node executors.

Each executor module registers itself via `@register_node(<type>)`, so importing
this package eagerly populates the global registry.
"""

# Order of imports matters when multiple executors share helpers.
from importlib import import_module

_EXECUTOR_MODULES = [
    "tool_node_executor",
    "llm_node_executor",
    "agent_node_executor",
    "loop_node_executor",
    "parallel_node_executor",
    "condition_node_executor",
    "workflow_node_executor",
    "code_node_executor",
    "human_node_executor",
    "monitor_node_executor",
    "swarm_node_executor",
    "recursive_node_executor",
]

_exports = {}
for _mod in _EXECUTOR_MODULES:
    _module = import_module(f"{__name__}.{_mod}")
    for _sym in getattr(_module, "__all__", []):
        if _sym in _exports:
            raise RuntimeError(f"Duplicate executor symbol: {_sym}")
        _exports[_sym] = getattr(_module, _sym)

# Export the canonical names (exact function identifiers)
globals().update(_exports)

# Additional convenience aliases without the `_node_` infix so
# tests and consumers can simply `import tool_executor` instead of the longer
# generated name. We keep this mapping local to this package.
for _name, _func in list(_exports.items()):
    if not _name.endswith("_node_executor"):
        continue
    _alias = _name.replace("_node_executor", "_executor")
    if _alias not in globals():
        globals()[_alias] = _func
        _exports[_alias] = _func

__all__ = sorted(_exports)
