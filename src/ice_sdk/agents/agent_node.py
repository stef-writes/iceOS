from __future__ import annotations

"""Lightweight AgentNode runtime stub.

The full reasoning/LLM execution will be implemented in v2.  For now this
placeholder satisfies type-checking, unit tests and orchestrator contracts.
"""

from datetime import datetime
from typing import Any, Dict, List

from ice_core.models.node_metadata import NodeMetadata

from ice_sdk.context import GraphContextManager
from ice_sdk.models.agent_models import AgentConfig
from ice_sdk.models.node_models import NodeExecutionResult

__all__ = ["AgentNode"]


class AgentNode:  # noqa: D101 – minimal stub
    def __init__(self, config: AgentConfig, context_manager: GraphContextManager):
        self.config = config
        self.context_manager = context_manager
        self.tools: List[Any] = []

    async def execute(self, context: Dict[str, Any] | None = None) -> NodeExecutionResult:  # noqa: D401
        """Return a dummy *NodeExecutionResult* for testing purposes."""

        now = datetime.utcnow()
        meta = NodeMetadata(  # type: ignore[call-arg]
            node_id=self.config.name or "agent",
            node_type="ai",
            start_time=now,
            end_time=now,
            duration=0.0,
        )
        return NodeExecutionResult(success=True, output=context or {}, metadata=meta) 