"""DEPRECATED shim – re-export from ``ice_sdk.orchestrator.workflow_execution_context``.
# ruff: noqa
"""

from warnings import warn

# Import canonical symbols before issuing warning to satisfy import-order rules.
from ice_sdk.orchestrator.workflow_execution_context import (  # noqa: E402
    WorkflowExecutionContext,
)

warn(
    "Importing from 'ice_orchestrator.workflow_execution_context' is deprecated; "
    "use 'ice_sdk.orchestrator.workflow_execution_context' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["WorkflowExecutionContext"]
