"""Stub NodeBuilderAgent used in tests."""

from __future__ import annotations

from typing import Any

from ...context import BaseAgent

__all__ = ["NodeBuilderAgent"]


class NodeBuilderAgent(BaseAgent):
    """Builds concrete node implementations from flow specs (stub)."""

    name = "node_builder"
    capabilities = ["node_generation", "code_synthesis"]
    version = "0.1"
    description = "Generates executable nodes from chain drafts"

    async def run(self, _spec: Any, **_kwargs: Any):  # noqa: D401 – stub
        return {
            "success": True,
            "message": "Nodes generated",
            "nodes": [],
        }
