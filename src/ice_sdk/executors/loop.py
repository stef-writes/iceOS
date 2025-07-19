from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, TypeAlias, TypeVar

# ---------------------------------------------------------------------------
# Fast test shortcut – when ICE_SDK_FAST_TEST=1 we skip heavy imports.
# ---------------------------------------------------------------------------


if os.getenv("ICE_SDK_FAST_TEST") == "1":

    # -------------------------------------------------------------------
    # Lightweight stub executor (avoids heavy deps during contract tests)
    # -------------------------------------------------------------------

    from typing import cast

    from ice_sdk.interfaces.chain import ScriptChainLike
    from ice_sdk.models.node_models import NodeExecutionResult  # lightweight import
    from ice_sdk.models.node_models import (
        ConditionNodeConfig,
        LLMOperatorConfig,
        NestedChainConfig,
        SkillNodeConfig,
    )

    # Reuse the real decorator so type signatures remain identical.
    from ice_sdk.node_registry import register_node  # type: ignore

    F = TypeVar("F")

    @dataclass(slots=True)
    class _LoopResult:  # noqa: D401 – helper stub
        success: bool
        output: list[Any]

    async def loop_executor(
        chain: "ScriptChainLike",  # match real signature exactly
        cfg: "LLMOperatorConfig | SkillNodeConfig | ConditionNodeConfig | NestedChainConfig",
        ctx: Dict[str, Any],
    ) -> NodeExecutionResult:  # noqa: D401 – stub matches real signature
        """Lightweight stub executor used in contract tests."""

        items = getattr(cfg, "items", None)
        if items is None:
            key = getattr(cfg, "iteration_key", None)
            if key:
                items = ctx.get(key, [])

        items = items or []

        # Convert stub result into *NodeExecutionResult* via cast to satisfy typing.
        return cast(NodeExecutionResult, _LoopResult(success=True, output=list(items)))

    # __all__ declared globally below

else:
    # -------------------------------------------------------------------
    # Full implementation (heavy imports permitted)
    # -------------------------------------------------------------------

    from ice_sdk.agents.loop_node import LoopNode
    from ice_sdk.interfaces.chain import ScriptChainLike
    from ice_sdk.models.node_models import (
        LLMOperatorConfig,
        NodeConfig,
        NodeExecutionResult,
    )
    from ice_sdk.node_registry import register_node

    # Local alias for type hints -----------------------------------------
    ScriptChain: TypeAlias = ScriptChainLike

    @register_node("loop")  # type: ignore[misc,type-var]  # decorator preserves signature
    async def loop_executor(
        chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
    ) -> NodeExecutionResult:
        """Executor for self-iterating *loop* nodes."""

        if not isinstance(cfg, LLMOperatorConfig):
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

    # __all__ declared globally below

# ---------------------------------------------------------------------------
# Module export list ---------------------------------------------------------
# ---------------------------------------------------------------------------
__all__: list[str] = ["loop_executor"]
