"""Ice Orchestrator package.

This package provides workflow orchestration capabilities for iceOS.
"""

# ruff: noqa: E402

# Prefer BaseWorkflow
from ice_orchestrator.base_workflow import BaseWorkflow, FailurePolicy  # type: ignore
from ice_orchestrator.workflow_execution_context import WorkflowExecutionContext

# Public contract facade (optional) ------------------------------------------
try:
    from ice_orchestrator.contracts.mvp_contract import MVPContract
except ModuleNotFoundError:  # pragma: no cover – optional component missing

    class MVPContract:  # type: ignore
        """Placeholder when *contracts* submodule is absent."""

        pass


# New exports ---------------------------------------------------------------
from .core.chain_registry import get_chain, list_chains, register_chain
from .core.network_factory import NetworkFactory
from .errors.chain_errors import ScriptChainError as ChainError
from .graph.dependency_graph import DependencyGraph

# existing exports
from .workflow import Workflow

# ---------------------------------------------------------------------------
# Runtime registration so lower layers can obtain the concrete implementation
# via ServiceLocator without violating layer boundaries.
# ---------------------------------------------------------------------------

try:
    # Registration is best-effort – in unit-test scenarios the SDK may not be
    # imported yet, so we guard against ImportError to avoid circular issues.
    from ice_sdk.services.locator import ServiceLocator

    ServiceLocator.register("workflow_proto", Workflow)  # type: ignore[arg-type]
except Exception:  # pragma: no cover – defensive: ignore if locator unavailable
    pass

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
