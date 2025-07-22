from importlib import import_module
from ice_core.models.node_models import NodeSpec, NodeType
from ice_sdk.registry.tool import global_tool_registry
from ice_sdk.registry.operator import global_operator_registry

"""Runtime node executors for the orchestrator layer.

Importing *ice_orchestrator.execution.executors* performs side-effects that
register all built-in node executors (ai/llm, tool/skill, condition, etc.)
with the global :pymod:`ice_sdk.registry.node` mapping.
"""

# Register built-in executor modules ----------------------------------------
_builtin = import_module(__name__ + ".builtin")

# Re-export canonical & deprecated executor callables -----------------------
llm_executor = getattr(_builtin, "llm_executor")  # type: ignore[attr-defined]
tool_executor = getattr(_builtin, "tool_executor")  # type: ignore[attr-defined]
import_module(__name__ + ".condition")

# Optional evaluator stub may be removed later
try:
    import_module(__name__ + ".evaluator")
except ModuleNotFoundError:  # pragma: no cover – optional stub
    pass

__all__ = [
    "llm_executor",  # canonical
    "tool_executor",
    "condition_executor",
    "evaluator_executor",
]
