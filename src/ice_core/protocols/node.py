"""Node protocol definition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from ice_core.models.node_models import NodeExecutionResult


class INode(ABC):
    """Core interface every node implements."""

    @abstractmethod
    async def validate(self) -> None:
        """Validate node configuration.

        Raises:
            ValidationError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> NodeExecutionResult:
        """Execute the node with given inputs.

        Args:
            inputs: Input data for the node

        Returns:
            NodeExecutionResult containing output and metadata
        """
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema for node inputs."""
        pass

    @property
    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """JSON schema for node outputs."""
        pass
