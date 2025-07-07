"""Ice Orchestrator package.

This package provides workflow orchestration capabilities for iceOS.
"""

from ice_sdk.orchestrator.base_script_chain import BaseScriptChain, FailurePolicy
from ice_sdk.orchestrator.workflow_execution_context import WorkflowExecutionContext

# New exports ---------------------------------------------------------------
from .core.chain_registry import get_chain, list_chains, register_chain  # noqa: F401
from .core.network_factory import NetworkFactory  # noqa: F401
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
    "register_chain",
    "get_chain",
    "list_chains",
    "NetworkFactory",
]
