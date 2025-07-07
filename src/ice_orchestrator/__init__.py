"""Ice Orchestrator package.

This package provides workflow orchestration capabilities for iceOS.
"""

from ice_sdk.orchestrator.base_script_chain import BaseScriptChain, FailurePolicy
from ice_sdk.orchestrator.workflow_execution_context import WorkflowExecutionContext

from .errors.chain_errors import ScriptChainError as ChainError
from .graph.dependency_graph import DependencyGraph
from .script_chain import ScriptChain  # noqa: F401 – re-export

__all__ = [
    "BaseScriptChain",
    "ScriptChain",
    "FailurePolicy",
    "ChainError",
    "DependencyGraph",
    "WorkflowExecutionContext",
]
