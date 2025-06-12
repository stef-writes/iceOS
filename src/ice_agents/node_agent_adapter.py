from __future__ import annotations

from typing import Any, Dict, Optional

from ice_sdk.models.node_models import NodeExecutionResult
from ice_sdk.context.session_state import SessionState
from ice_sdk.base_node import BaseNode


class NodeAgentAdapter:
    """Thin wrapper that exposes a :class:`BaseNode` through an *agent-like* interface.

    The goal is to make a node usable anywhere an "agent" (as described in Google ADK)
    is expected **without changing the underlying node implementation**.  It keeps the
    public surface minimal so that we can iterate without lock-in:

    - ``name``:     Machine-readable identifier (defaults to ``node.id``)
    - ``describe``: Short human-readable description (optional)
    - ``execute``:  Asynchronous call accepting *input context* and returning the
                    wrapped node's :class:`NodeExecutionResult` (unmodified).
    """

    def __init__(
        self,
        node: BaseNode,
        *,
        name: Optional[str] = None,
        description: str | None = None,
    ) -> None:
        self._node = node
        self._name = name or getattr(node, "id", node.__class__.__name__)
        # Prefer config.description if available
        self._description = (
            description
            or getattr(getattr(node, "config", object()), "description", None)
            or ""
        )

    # ---------------------------------------------------------------------
    # Public properties
    # ---------------------------------------------------------------------
    @property
    def name(self) -> str:  # noqa: D401
        """Unique identifier used by routers / planners."""
        return self._name

    @property
    def description(self) -> str:  # noqa: D401
        """Optional human-readable summary."""
        return self._description

    @property
    def node(self) -> BaseNode:  # noqa: D401
        """Access to the underlying node (read-only).

        Keep this *public* but discourage direct modification so that callers
        can still introspect configuration, schemas, etc.
        """
        return self._node

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    async def execute(
        self,
        session: SessionState | None,
        input_context: Dict[str, Any] | None = None,
        **kwargs,
    ) -> NodeExecutionResult:
        """Run the underlying node and optionally persist to *session* state."""
        input_context = input_context or {}
        # Merge with last output if caller requests (simple example)
        if session is not None and self.name in session.last_outputs:
            input_context.setdefault("_last_output", session.last_outputs[self.name])

        result = await self._node.execute(input_context, **kwargs)  # type: ignore[arg-type]

        # Persist output into session memory --------------------------------
        if session is not None and result.success:
            session.set_output(self.name, result.output)

        return result

    # ------------------------------------------------------------------
    # Helpers / dunder methods
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # noqa: D401
        return (
            f"<NodeAgentAdapter name={self.name!r} node={self.node.__class__.__name__}>"
        )
