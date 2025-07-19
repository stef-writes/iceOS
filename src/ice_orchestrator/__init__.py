"""Ice Orchestrator package.

This package provides workflow orchestration capabilities for iceOS.
"""

# ruff: noqa: E402

import warnings

# Emit deprecation notice once per import
warnings.warn(
    "`ice_orchestrator.ScriptChain` is deprecated; use `ice_orchestrator.Workflow` instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Public contract facade ------------------------------------------------------
from ice_core.contracts.mvp_contract import MVPContract  # noqa: F401

# Prefer BaseWorkflow
from ice_sdk.orchestrator.base_workflow import (  # type: ignore
    BaseWorkflow,
    FailurePolicy,
)
from ice_sdk.orchestrator.workflow_execution_context import WorkflowExecutionContext

# New exports ---------------------------------------------------------------
from .core.chain_registry import get_chain, list_chains, register_chain  # noqa: F401
from .core.network_factory import NetworkFactory  # noqa: F401
from .errors.chain_errors import ScriptChainError as ChainError
from .graph.dependency_graph import DependencyGraph

# existing exports
from .workflow import Workflow

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
    "MVPContract",
]
