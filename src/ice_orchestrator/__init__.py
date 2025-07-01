"""Ice Orchestrator package.

This package provides workflow orchestration capabilities for iceOS.
"""

from ice_sdk.orchestrator.base_script_chain import BaseScriptChain, FailurePolicy

from .chain_errors import ScriptChainError as ChainError
from .node_dependency_graph import DependencyGraph
from .script_chain import ScriptChain  # noqa: F401 – re-export
from .workflow_execution_context import WorkflowExecutionContext

__all__ = [
    "BaseScriptChain",
    "ScriptChain",
    "FailurePolicy",
    "ChainError",
    "DependencyGraph",
    "WorkflowExecutionContext",
]
