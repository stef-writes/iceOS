from importlib import import_module
from ice_core.unified_registry import registry
from ice_core.unified_registry import registry
from ice_core.models import NodeType

# Import tool modules to register them
import ice_sdk.tools.system

"""Runtime node executors for the orchestrator layer.

Importing ice_orchestrator.execution.executors registers all built-in node executors
with the unified registry.
"""

# Import unified executors for new node system
_unified = import_module(__name__ + ".unified")
from .unified import (
    tool_executor,
    llm_executor,
    agent_executor,
    condition_executor,
    workflow_executor,
    loop_executor,
    parallel_executor,
    code_executor,
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
