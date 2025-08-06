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

    # Public-ish attributes accessed by ice_builder
    context_manager: Any
    _agent_cache: dict[str, Any]
    _chain_tools: list[Any]

    # Methods that are directly invoked
    async def execute_node(
        self, node_id: str, context: dict[str, Any]
    ) -> Any:  # pragma: no cover
        ...

    async def execute_node_config(
        self,
        node_config: Any,
        context: dict[str, Any],
        *,
        parent_id: str | None = None,
    ) -> Any:  # pragma: no cover – orchestration internals
        ...
