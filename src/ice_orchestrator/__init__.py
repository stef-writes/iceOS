"""Ice Orchestrator package.

This package provides workflow orchestration capabilities for iceOS.
"""

import warnings

# Emit deprecation notice once per import
warnings.warn(
    "`ice_orchestrator.ScriptChain` is deprecated; use `ice_orchestrator.Workflow` instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Prefer BaseWorkflow
from ice_sdk.orchestrator.base_workflow import BaseWorkflow, FailurePolicy  # type: ignore

# Public re-export
from .workflow import Workflow

# New exports ---------------------------------------------------------------
from .core.chain_registry import get_chain, list_chains, register_chain  # noqa: F401
from .core.network_factory import NetworkFactory  # noqa: F401
from ice_sdk.orchestrator.workflow_execution_context import WorkflowExecutionContext
from .errors.chain_errors import ScriptChainError as ChainError
from .graph.dependency_graph import DependencyGraph

# Deprecated alias for backward-compat ------------------------------------------------
ScriptChain = Workflow  # type: ignore

__all__ = [
    "BaseWorkflow",
    "Workflow",
    "FailurePolicy",
    "ChainError",
    "DependencyGraph",
    "WorkflowExecutionContext",
    "register_chain",
    "get_chain",
    "list_chains",
    "NetworkFactory",
]
