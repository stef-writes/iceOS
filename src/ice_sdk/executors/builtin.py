# ruff: noqa: E402
from __future__ import annotations

"""Built-in node executors for *ice_sdk*.

The module is imported for its side-effects by :pymod:`ice_sdk.executors`.
It registers executors for the two node modes that ship with the SDK:

* ``ai``   – LLM-powered agent node
* ``tool`` – deterministic tool invocation
"""

from datetime import datetime
from typing import Any, Dict, TypeAlias

from ice_sdk.agents.agent_node import AgentNode
from ice_sdk.interfaces.chain import ScriptChainLike
from ice_sdk.models.agent_models import AgentConfig, ModelSettings
from ice_sdk.models.node_models import (
    AiNodeConfig,
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from ice_sdk.node_registry import register_node
from ice_sdk.tools.base import BaseTool
from ice_sdk.utils.prompt_renderer import render_prompt

# Alias used in annotations locally ------------------------------------------
ScriptChain: TypeAlias = ScriptChainLike

# ---------------------------------------------------------------------------
# Helper – build AgentNode from AiNodeConfig (duplicated from ScriptChain._make_agent)
# ---------------------------------------------------------------------------


def _build_agent(chain: ScriptChain, node: AiNodeConfig) -> AgentNode:
    """Build or fetch a cached AgentNode instance for *node*."""
    agent_cache: Dict[str, AgentNode] = getattr(chain, "_agent_cache")
    existing = agent_cache.get(node.id)
    if existing is not None:
        return existing

    # Build precedence-aware tool map ------------------------------------
    tool_map: Dict[str, BaseTool] = {}

    # 1. Globally registered tools (lowest precedence) -------------------
    for name, tool in chain.context_manager.get_all_tools().items():
        tool_map[name] = tool

    # 2. Chain-level tools — override when name clashes ------------------
    for t in getattr(chain, "_chain_tools", []):
        tool_map[t.name] = t

    # 3. Node-specific tool references — highest precedence -------------
    if node.tools:
        for cfg in node.tools:  # type: ignore[attr-defined]
            t_obj = chain.context_manager.get_tool(cfg.name)
            if t_obj is not None:
                tool_map[t_obj.name] = t_obj

    tools: list[BaseTool] = list(tool_map.values())

    model_settings = ModelSettings(
        model=node.model,
        temperature=getattr(node, "temperature", 0.7),
        max_tokens=getattr(node, "max_tokens", None),
        provider=str(getattr(node.provider, "value", node.provider)),
    )

    agent_cfg = AgentConfig(
        name=node.name or node.id,
        instructions=node.prompt,
        model=node.model,
        model_settings=model_settings,
        tools=tools,
    )  # type: ignore[call-arg]

    agent = AgentNode(config=agent_cfg, context_manager=chain.context_manager)
    agent.tools = tools

    # Register with context manager
    try:
        chain.context_manager.register_agent(agent)
    except ValueError:
        pass

    for tool in tools:
        try:
            chain.context_manager.register_tool(tool)
        except ValueError:
            continue

    agent_cache[node.id] = agent
    return agent


# ---------------------------------------------------------------------------
# "ai" executor ------------------------------------------------------------
# ---------------------------------------------------------------------------


@register_node("ai")
async def ai_executor(
    chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Executor for LLM-powered *ai* nodes."""

    if not isinstance(cfg, AiNodeConfig):
        raise TypeError("ai_executor received incompatible cfg type")

    # ------------------------------------------------------------------
    # Dynamic prompt templating ----------------------------------------
    # ------------------------------------------------------------------
    # *render_prompt* substitutes any placeholder expressions in the
    # ``cfg.prompt`` string using the *ctx* dict prepared by ScriptChain.
    # The helper falls back to the original string if rendering fails so
    # we never break node execution due to missing keys.

    try:
        cfg.prompt = await render_prompt(cfg.prompt, ctx)  # type: ignore[assignment]
    except Exception:
        # Defensive: keep original prompt on any rendering error.
        pass

    agent = _build_agent(chain, cfg)
    return await agent.execute(ctx)


# ---------------------------------------------------------------------------
# "tool" executor ----------------------------------------------------------
# ---------------------------------------------------------------------------


@register_node("tool")
async def tool_executor(
    chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Executor for deterministic tool nodes with context-aware `tool_args`."""

    from ice_sdk.models.node_models import ToolNodeConfig

    if not isinstance(cfg, ToolNodeConfig):
        raise TypeError("tool_executor received incompatible cfg type")

    def _apply_ctx(value: Any) -> Any:  # noqa: D401 – helper
        """Recursively substitute `{key}` placeholders using *ctx*."""
        if isinstance(value, str):
            try:
                return value.format(**ctx)
            except Exception:
                return value  # leave unchanged if placeholder missing
        if isinstance(value, dict):
            return {k: _apply_ctx(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_apply_ctx(v) for v in value]
        return value

    tool_name = cfg.tool_name
    raw_args = cfg.tool_args or {}
    tool_args = _apply_ctx(raw_args)

    output = await chain.context_manager.execute_tool(tool_name, **tool_args)

    result = NodeExecutionResult(  # type: ignore[call-arg]
        success=True,
        output=output,
        metadata=NodeMetadata(  # type: ignore[call-arg]
            node_id=cfg.id,
            node_type="tool",
            name=cfg.name,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
        ),
        execution_time=0.0,
    )
    return result
