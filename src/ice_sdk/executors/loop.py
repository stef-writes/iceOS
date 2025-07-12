from __future__ import annotations

from typing import Any, Dict, TypeAlias

from ice_sdk.agents.loop_node import LoopNode
from ice_sdk.interfaces.chain import ScriptChainLike
from ice_sdk.models.node_models import AiNodeConfig, NodeConfig, NodeExecutionResult
from ice_sdk.node_registry import register_node

# Local alias for type hints --------------------------------------------------
ScriptChain: TypeAlias = ScriptChainLike


@register_node("loop")  # type: ignore[misc]  # decorator preserves signature
async def loop_executor(
    chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Executor for self-iterating *loop* nodes.

    Reuses the `_build_agent` helper from :pymod:`ice_sdk.executors.builtin` to
    keep tool resolution logic in a single place, then upgrades the resulting
    :class:`AgentNode` to :class:`LoopNode`.
    """

    if not isinstance(cfg, AiNodeConfig):
        raise TypeError("loop_executor received incompatible cfg type")

    # Lazy import to avoid circular dep -------------------------------------
    from ice_sdk.executors.builtin import _build_agent

    base_agent = _build_agent(chain, cfg)

    # Upgrade to LoopNode ----------------------------------------------------
    loop_agent = LoopNode(
        config=base_agent.config,
        context_manager=base_agent.context_manager,
        llm_service=base_agent.llm_service,
    )
    loop_agent.tools = base_agent.tools  # Preserve tool whitelist

    return await loop_agent.execute(ctx)
