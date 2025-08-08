"""Registry protocol definition."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, List, Optional, Protocol, Type

from ice_core.models.enums import NodeType


class IRegistry(Protocol):
    """Protocol for node registry implementations.

    Registries manage the registration and retrieval of node classes
    and instances by type and name.
    """

    @abstractmethod
    def register_class(
        self, node_type: NodeType, name: str, cls: Type[Any], force: bool = False
    ) -> None:
        """Register a node class.

        Args:
            node_type: Type of node being registered
            name: Unique name for the node
            cls: The class to register
            force: If True, overwrites existing registration

        Raises:
            RegistryError: If name already registered and force=False
        """
        ...

    # Legacy instance API removed – factories are the only registration path

    @abstractmethod
    def get_class(self, node_type: NodeType, name: str) -> Type[Any]:
        """Get a registered node class.

        Args:
            node_type: Type of node to retrieve
            name: Name of the node

        Returns:
            The registered class

        Raises:
            RegistryError: If not found
        """
        ...

    # Legacy instance API removed – factories are the only retrieval path

    @abstractmethod
    def get_agent_class(self, name: str) -> type:
        """Return the imported agent class for *name* (lazy import)."""
        ...

    @abstractmethod
    def list_agents(self) -> List[str]:
        """List registered agent names."""
        ...

    @abstractmethod
    def list_nodes(self, node_type: Optional[NodeType] = None) -> List[str]:
        """List all registered nodes.

        Args:
            node_type: If provided, filter by this type

        Returns:
            List of registered node names
        """
        ...
