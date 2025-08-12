"""Executor protocol definition.

Execution engines transform *nodes* into *NodeExecutionResult*s. This protocol
allows the orchestrator to treat heterogeneous executors uniformly and to pick
an engine at runtime based on `supports(node)` semantics.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Protocol

from ice_core.models.node_models import NodeExecutionResult

from .node import INode


class IExecutor(Protocol):
    """Contract for node execution engines."""

    # ------------------------------------------------------------------
    # Capability discovery
    # ------------------------------------------------------------------

    @abstractmethod
    def supports(self, node: INode) -> bool:
        """Return True if this executor can handle *node*."""

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    @abstractmethod
    async def execute(self, node: INode, inputs: Dict[str, Any]) -> NodeExecutionResult:  # noqa: D401
        """Execute *node* with *inputs* and return a structured result."""
