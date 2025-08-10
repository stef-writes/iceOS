"""Tool protocol definition."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Optional, Protocol


class ITool(Protocol):
    """Protocol for all tool implementations.

    Tools are stateless, idempotent operations that can have side effects.
    They must define their input/output schemas and implement the execute method.
    """

    # Required attributes
    name: str
    description: str

    @abstractmethod
    async def execute(
        self,
        input_data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the tool with given inputs.

        Args:
            input_data: Legacy payload mapping (merged with kwargs)
            idempotency_key: Optional key for caching/idempotency
            **kwargs: Direct keyword parameters

        Returns:
            Dict containing the tool's output
        """
        ...

    @classmethod
    @abstractmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool inputs."""
        ...

    @classmethod
    @abstractmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool outputs."""
        ...
