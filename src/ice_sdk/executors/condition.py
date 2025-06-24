from __future__ import annotations

"""Executor for *condition* nodes that decide control-flow based on a boolean
expression evaluated against the assembled input context.
"""

from datetime import datetime
from typing import Any, Dict, TypeAlias

from ice_sdk.interfaces.chain import ScriptChainLike
from ice_sdk.models.node_models import (
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
    ConditionNodeConfig,
)
from ice_sdk.node_registry import register_node

ScriptChain: TypeAlias = ScriptChainLike


@register_node("condition")
async def condition_executor(
    chain: ScriptChain,
    cfg: NodeConfig,  # accepts any, runtime check below
    ctx: Dict[str, Any],
) -> NodeExecutionResult:  # noqa: D401
    """Evaluate *cfg.expression* in a limited sandbox.

    The execution context is the *ctx* dict; built-ins and globals are stripped.
    Any exception during evaluation marks the node as failed.
    """

    if not isinstance(cfg, ConditionNodeConfig):
        raise TypeError("condition_executor received incompatible cfg type")

    start = datetime.utcnow()

    # ------------------------------------------------------------------
    # Primitive sandbox – drop builtins, expose only ctx -----------------
    # ------------------------------------------------------------------
    sandbox_globals: Dict[str, Any] = {}
    sandbox_locals = dict(ctx)  # copy to avoid mutation

    try:
        result = bool(eval(cfg.expression, sandbox_globals, sandbox_locals))  # noqa: S307
        success = True
        error_msg: str | None = None
    except Exception as exc:  # pylint: disable=broad-except
        result = False
        success = False
        error_msg = f"Condition evaluation failed: {exc}"

    end = datetime.utcnow()

    metadata = NodeMetadata(  # type: ignore[call-arg]
        node_id=cfg.id,
        node_type="condition",
        name=cfg.name,
        start_time=start,
        end_time=end,
    )

    return NodeExecutionResult(  # type: ignore[call-arg]
        success=success,
        error=error_msg,
        output={"result": result},
        metadata=metadata,
        execution_time=(end - start).total_seconds(),
    ) 