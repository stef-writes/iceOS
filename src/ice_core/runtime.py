"""Runtime wiring for concrete orchestrator implementations.

This module is intentionally *empty* (all ``None`` by default) at import
time.  The runtime layer (e.g. *ice_orchestrator*) **must** assign the
factories/services during its startup sequence.

The compile-time layers import *only type annotations* from
``ice_core.protocols.runtime_factories`` – avoiding any hard dependency
on the orchestrator package.
"""

from __future__ import annotations

from typing import Any, Optional

from ice_core.protocols.runtime_factories import (
    NetworkCoordinatorFactory,
    ToolExecutionServiceProtocol,
    WorkflowFactory,
)

workflow_factory: Optional[WorkflowFactory] = None
network_coordinator_factory: Optional[NetworkCoordinatorFactory] = None
tool_execution_service: Optional[ToolExecutionServiceProtocol] = None

# Additional runtime-wired services for top-level API usage
context_manager: Optional[Any] = None
workflow_execution_service: Optional[Any] = None
