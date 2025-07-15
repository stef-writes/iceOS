"""Stub PromptEngineerAgent used in integration tests."""

from __future__ import annotations

from typing import Any

from ...context import BaseAgent

__all__ = ["PromptEngineerAgent"]


class PromptEngineerAgent(BaseAgent):
    """Optimises prompts for LLM calls (stub)."""

    name = "prompt_engineer"
    capabilities = ["prompt_optimisation"]
    version = "0.1"
    description = "Optimises LLM prompts for accuracy/cost"

    async def run(
        self, _spec: Any, **_kwargs: Any
    ) -> dict[str, Any]:  # noqa: D401 – stub
        return {"success": True, "prompt": "optimised"}
