"""Workflow protocol definitions."""
from __future__ import annotations

from typing import Any, Protocol


class IWorkflow(Protocol):
    """Workflow protocol for execution engines."""
    pass

class WorkflowLike(Protocol):
    """Minimal subset of workflow functionality used by SDK.

    This protocol lets us keep type hints while avoiding circular imports
    between SDK and orchestrator layers.
    """

    # Public-ish attributes accessed by ice_sdk
    context_manager: Any
    _agent_cache: dict[str, Any]
    _chain_tools: list[Any]

    # Methods that are directly invoked
    # (currently none; extend when needed)

 