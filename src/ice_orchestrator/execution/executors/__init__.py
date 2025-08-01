from importlib import import_module

# Import tool modules to register them

"""Runtime node executors for the orchestrator layer.

Importing ice_orchestrator.execution.executors registers all built-in node executors
with the unified registry.
"""

# Import unified executors for new node system
_unified = import_module(__name__ + ".unified")
from .unified import (
    agent_executor,
    code_executor,
    condition_executor,
    llm_executor,
    loop_executor,
    parallel_executor,
    tool_executor,
    workflow_executor,
)

# Evaluator functionality integrated into main executors
evaluator_executor = None  # type: ignore

__all__ = [
    "tool_executor",
    "llm_executor",
    "agent_executor",
    "condition_executor",
    "workflow_executor",
    "loop_executor",
    "parallel_executor",
    "code_executor",
]
