"""Chain-related error classes for the orchestrator."""

from ice_core.exceptions import IceCoreError


class ChainError(IceCoreError):
    """Base class for chain execution errors."""
    pass


class ChainValidationError(ChainError):
    """Error raised when chain validation fails."""
    pass


class ChainExecutionError(ChainError):
    """Error raised during chain execution."""
    pass


class NodeExecutionError(ChainError):
    """Error raised during node execution within a chain."""
    
    def __init__(self, message: str, node_id: str, node_type: str = "unknown"):
        super().__init__(message)
        self.node_id = node_id
        self.node_type = node_type 