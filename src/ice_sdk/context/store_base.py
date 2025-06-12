from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseContextStore(ABC):
    """Abstract base class for context storage backends."""

    @abstractmethod
    def get(self, node_id: str) -> Any:
        """Retrieve context data for a node."""
        pass

    @abstractmethod
    def set(self, node_id: str, context: Dict[str, Any]) -> None:
        """Set context data for a node."""
        pass

    @abstractmethod
    def update(
        self, node_id: str, content: Any, execution_id: Optional[str] = None
    ) -> None:
        """Update context data for a node, optionally with an execution ID."""
        pass

    @abstractmethod
    def clear(self, node_id: Optional[str] = None) -> None:
        """Clear context for a specific node or all nodes."""
        pass
