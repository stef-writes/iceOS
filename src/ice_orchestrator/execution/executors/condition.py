from __future__ import annotations

# ruff: noqa: E402

"""Executor for *condition* nodes – moved from SDK layer."""

from datetime import datetime
from typing import Any, Dict, TypeAlias

from ice_core.models import ConditionNodeConfig, NodeConfig, NodeExecutionResult
from ice_core.models.node_models import NodeMetadata
from ice_sdk.interfaces.chain import ScriptChainLike
from ice_sdk.registry.node import register_node

ScriptChain: TypeAlias = ScriptChainLike


@register_node("condition")  # type: ignore[misc,type-var]
async def condition_executor(
    chain: ScriptChain,
    cfg: NodeConfig,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:
    """Evaluate *cfg.expression* in a limited sandbox."""

    if not isinstance(cfg, ConditionNodeConfig):
        raise TypeError("condition_executor received incompatible cfg type")

    start = datetime.utcnow()

    # Secure evaluation --------------------------------------------------
    sandbox_locals = dict(ctx)

    try:
        from restrictedpython import compile_restricted  # type: ignore

        byte_code = compile_restricted(
            cfg.expression, filename="<condition>", mode="eval"
        )
        sandbox_globals: Dict[str, Any] = {"__builtins__": {}}
        result = bool(eval(byte_code, sandbox_globals, sandbox_locals))
        success = True
        error_msg: str | None = None
    except ModuleNotFoundError:
        sandbox_globals = {"__builtins__": {}}
        try:
            result = bool(eval(cfg.expression, sandbox_globals, sandbox_locals))
            success = True
            error_msg = None
        except Exception as exc:
            result = False
            success = False
            error_msg = f"Condition evaluation failed: {exc}"
    except Exception as exc:
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
