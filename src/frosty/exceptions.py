"""Frosty-specific exception types (minimal stub)."""


class AgentNotFoundError(Exception):
    """Raised when a requested agent is not registered in the context."""


class FrostyError(Exception):
    """Generic Frosty runtime error."""
