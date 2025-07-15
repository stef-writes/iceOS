"""Stub FlowDesignAgent matching the public tests."""

from __future__ import annotations

from typing import Any

from ...context import BaseAgent

__all__ = ["FlowDesignAgent"]


class FlowDesignAgent(BaseAgent):
    """Minimal flow-design agent used in open-source contract tests."""

    name = "flow_design"
    capabilities = ["chain_design", "goal_interpretation"]
    version = "0.1"
    description = "Generates initial chain drafts from high-level goals"

    async def run(self, _spec: Any, **_kwargs: Any):  # noqa: D401 – stub
        # Return a fake chain draft
        return {
            "success": True,
            "message": "Draft generated",
            "chain_spec": {
                "name": "draft",
                "nodes": [],
            },
        }
