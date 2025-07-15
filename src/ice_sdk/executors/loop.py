from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, TypeAlias

# ---------------------------------------------------------------------------
# Fast test shortcut – when ICE_SDK_FAST_TEST=1 we skip heavy imports.
# ---------------------------------------------------------------------------


if os.getenv("ICE_SDK_FAST_TEST") == "1":

    # -------------------------------------------------------------------
    # Lightweight stub executor (avoids heavy deps during contract tests)
    # -------------------------------------------------------------------

    register_node = lambda *args, **kwargs: lambda fn: fn  # type: ignore  # noqa: E731

    @dataclass(slots=True)
    class _LoopResult:  # noqa: D401 – helper
        success: bool
        output: list[Any]

    async def loop_executor(_chain: Any, cfg: Any, ctx: Dict[str, Any]):  # type: ignore[override]  # noqa: D401
        """Lightweight stub executor used in contract tests."""

        items = getattr(cfg, "items", None)
        if items is None:
            key = getattr(cfg, "iteration_key", None)
            if key:
                items = ctx.get(key, [])

        items = items or []
        return _LoopResult(success=True, output=list(items))

    __all__: list[str] = ["loop_executor"]

else:
    # -------------------------------------------------------------------
    # Full implementation (heavy imports permitted)
    # -------------------------------------------------------------------

    from ice_sdk.agents.loop_node import LoopNode
    from ice_sdk.interfaces.chain import ScriptChainLike
    from ice_sdk.models.node_models import AiNodeConfig, NodeConfig, NodeExecutionResult
    from ice_sdk.node_registry import register_node

    # Local alias for type hints -----------------------------------------
    ScriptChain: TypeAlias = ScriptChainLike

    @register_node("loop")  # type: ignore[misc]  # decorator preserves signature
    async def loop_executor(
        chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
    ) -> NodeExecutionResult:
        """Executor for self-iterating *loop* nodes."""

        if not isinstance(cfg, AiNodeConfig):
            raise TypeError("loop_executor received incompatible cfg type")

        # Lazy import to avoid circular dep ------------------------------
        from ice_sdk.executors.builtin import _build_agent

        base_agent = _build_agent(chain, cfg)

        # Upgrade to LoopNode -------------------------------------------
        loop_agent = LoopNode(
            config=base_agent.config,
            context_manager=base_agent.context_manager,
            llm_service=base_agent.llm_service,
        )
        loop_agent.tools = base_agent.tools  # Preserve tool whitelist

        return await loop_agent.execute(ctx)

    __all__: list[str] = ["loop_executor"]
