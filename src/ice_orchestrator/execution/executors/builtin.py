# ruff: noqa: E402
from __future__ import annotations

"""Built-in node executors for *ice_orchestrator*.

Moved from :pymod:`ice_sdk.executors.builtin` to keep runtime code inside the
orchestrator layer.
"""

# Standard library imports -----------------------------------------------------
import re
import warnings
from datetime import datetime
from typing import Any, Dict, TypeAlias

from ice_core.models import (
    LLMOperatorConfig,
    NodeConfig,
    NodeExecutionResult,
    SkillNodeConfig,
)
from ice_core.models.node_models import NestedChainConfig, NodeMetadata

# Node registry decorator remains
from ice_sdk.registry.node import register_node

# Prompt rendering and LLM service helpers
from ice_sdk.utils.prompt_renderer import render_prompt
from ice_sdk.providers.llm_service import LLMService
from ice_core.registry.prompt_template import global_prompt_template_registry

# For type aliasing of script chains (keeps previous behaviour)
from ice_sdk.interfaces.chain import WorkflowLike as _WorkflowLike

# Alias used in annotations locally ------------------------------------------
ScriptChain: TypeAlias = _WorkflowLike

# ---------------------------------------------------------------------------
# "llm" executor ------------------------------------------------------------
# ---------------------------------------------------------------------------


@register_node("llm")  # canonical discriminator  # type: ignore[type-var]
async def llm_executor(  # type: ignore[type-var]
    chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Executor for LLM-powered ``llm`` nodes."""

    if not isinstance(cfg, LLMOperatorConfig):
        raise TypeError("llm_executor received incompatible cfg type")

    # ------------------------------------------------------------------
    # Resolve template references & dynamic prompt rendering ------------
    # ------------------------------------------------------------------

    prompt_source = cfg.prompt

    if prompt_source.startswith("template:"):
        tpl_name = prompt_source.split(":", 1)[1].strip()
        tpl_obj = global_prompt_template_registry.get(tpl_name)
        prompt_source = tpl_obj.format(**ctx)

    # *render_prompt* substitutes {{ placeholders }} using the context.
    # It falls back to the original string if rendering fails so we never
    # break node execution due to missing keys.

    # Render template ---------------------------------------------------
    rendered_prompt: str
    try:
        rendered_prompt = await render_prompt(prompt_source, ctx)
    except Exception:
        rendered_prompt = prompt_source

    # After rendering, ensure no unresolved placeholders remain ---------
    _LEFTOVER_RE = re.compile(r"\{\s*[a-zA-Z0-9_\.]+\s*\}")
    if _LEFTOVER_RE.search(rendered_prompt):
        raise ValueError(
            f"Prompt for node '{cfg.id}' contains unresolved placeholders after rendering: {rendered_prompt}"
        )

    cfg.prompt = rendered_prompt  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Call provider-specific LLM service directly -----------------------
    # ------------------------------------------------------------------

    llm_service = LLMService()

    tools_payload = [t.model_dump() for t in (cfg.tools or [])]  # type: ignore[attr-defined]

    text, usage_stats, error_msg = await llm_service.generate(
        llm_config=cfg.llm_config,
        prompt=rendered_prompt,
        context=ctx,
        tools=tools_payload or None,
        timeout_seconds=getattr(cfg, "timeout_seconds", 30),
        max_retries=getattr(cfg, "retries", 2),
    )

    success_flag = error_msg is None or error_msg == ""

    return NodeExecutionResult(  # type: ignore[call-arg]
        success=success_flag,
        error=error_msg,
        output={"text": text, "usage": usage_stats},
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type="llm",
            name=cfg.name,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
        ),
        execution_time=0.0,
    )


# ---------------------------------------------------------------------------
# "tool" executor ----------------------------------------------------------
# ---------------------------------------------------------------------------


@register_node("tool")  # canonical discriminator  # type: ignore[type-var]
async def tool_executor(  # type: ignore[type-var]
    chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Executor for deterministic tool nodes with context-aware `tool_args`."""

    if not isinstance(cfg, SkillNodeConfig):
        raise TypeError("tool_executor received incompatible cfg type")

    def _apply_ctx(value: Any) -> Any:  # – helper
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

    tool_name = cfg.tool_name  # type: ignore[attr-defined]
    raw_args = getattr(cfg, "tool_args", {}) or {}
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


# ---------------------------------------------------------------------------
# "nested_chain" executor ----------------------------------------------------
# ---------------------------------------------------------------------------


@register_node("nested_chain")  # type: ignore[misc,type-var]  # decorator preserves signature
async def nested_chain_executor(
    chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Executor that runs a *nested* ScriptChain.

    The nested chain instance (or a zero-argument factory) is provided via
    :class:`~ice_sdk.models.node_models.NestedChainConfig.chain`.
    Input mappings are handled upstream by :class:`ScriptChain`; *ctx* is
    therefore the fully-rendered input for the child chain.
    """

    if not isinstance(cfg, NestedChainConfig):
        raise TypeError("nested_chain_executor received incompatible cfg type")

    # Resolve child chain instance ------------------------------------------------
    child = cfg.chain  # could be ScriptChain or factory

    try:
        child_chain: ScriptChain = child() if callable(child) else child  # type: ignore[operator]
    except Exception as exc:  # pragma: no cover – defensive
        raise RuntimeError(
            f"Failed to instantiate nested chain for node '{cfg.id}': {exc}"
        ) from exc

    # Best-effort: update child context with *ctx* --------------------------------
    try:
        from ice_sdk.context import (  # imported here to avoid heavy deps at module import
            GraphContextManager,
        )
        from ice_sdk.context.manager import GraphContext

        cm = GraphContextManager()
        cm.set_context(
            GraphContext(
                session_id=f"nested_{cfg.id}",
                metadata=ctx,
                execution_id=f"nested_{cfg.id}_{datetime.utcnow().isoformat()}",
            )
        )
        child_chain.context_manager = cm  # type: ignore[assignment]
    except (
        Exception
    ):  # pragma: no cover – never abort parent chain due to context issues
        pass

    # Execute child chain ---------------------------------------------------------
    child_result = await child_chain.execute()  # type: ignore[attr-defined]

    # Apply *exposed_outputs* mapping when present ---------------------------------
    output_payload: Any = child_result.output
    if cfg.exposed_outputs and isinstance(output_payload, dict):
        try:
            import jmespath  # optional dependency – only used when mapping requested

            mapped: Dict[str, Any] = {}
            for public_key, query in cfg.exposed_outputs.items():
                mapped[public_key] = jmespath.search(query, output_payload)
            output_payload = mapped
        except Exception:
            # Silently ignore mapping errors – propagate raw output
            pass

    # Wrap into parent-level result ------------------------------------------------
    result = NodeExecutionResult(  # type: ignore[call-arg]
        success=child_result.success,
        error=child_result.error,
        output=output_payload,
        metadata=NodeMetadata(  # type: ignore[call-arg]
            node_id=cfg.id,
            node_type="nested_chain",
            name=cfg.name,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
        ),
        execution_time=child_result.execution_time,
    )
    return result
