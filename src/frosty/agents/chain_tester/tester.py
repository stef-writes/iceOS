"""Stub ChainTesterAgent used in integration tests."""

from __future__ import annotations

from typing import Any

from ...context import BaseAgent

__all__ = ["ChainTesterAgent"]


class ChainTesterAgent(BaseAgent):
    """Runs chain-level test cases (stub)."""

    name = "chain_tester"
    capabilities = ["chain_testing"]
    version = "0.1"
    description = "Executes tests against generated chains"

    async def run(self, _spec: Any, **_kwargs: Any):  # noqa: D401 – stub
        return {"success": True, "tests_passed": True}
