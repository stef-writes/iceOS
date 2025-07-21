from importlib import import_module

"""Runtime node executors for the orchestrator layer.

Importing *ice_orchestrator.execution.executors* performs side-effects that
register all built-in node executors (ai/llm, tool/skill, condition, etc.)
with the global :pymod:`ice_sdk.registry.node` mapping.
"""

# Register built-in executor modules ----------------------------------------
import_module(__name__ + ".builtin")
import_module(__name__ + ".condition")

# Optional evaluator stub may be removed later
try:
    import_module(__name__ + ".evaluator")
except ModuleNotFoundError:  # pragma: no cover – optional stub
    pass

__all__ = [
    "ai_executor",
    "tool_executor",
    "condition_executor",
    "evaluator_executor",
]
