"""Built-in executor for *agent* nodes.

Implements charter §9.2 task #2 – executes a user-supplied agent class
referenced by :class:`ice_core.models.node_models.PrebuiltAgentConfig`.

The executor performs four steps:
1. Dynamically imports the configured package and retrieves the agent class/obj.
2. Runs `validate()` if present (Rule 13).
3. Invokes `execute(context)` (async-aware).
4. Wraps the result into :class:`NodeExecutionResult`.
"""

from __future__ import annotations

import asyncio
import importlib
from datetime import datetime
from types import ModuleType
from typing import Any, Dict, TypeAlias

from ice_core.models import NodeExecutionResult, PrebuiltAgentConfig
from ice_core.models.node_models import NodeMetadata

from ice_sdk.registry.node import register_node

# For typing compatibility with orchestrator internals -----------------------
from ice_sdk.interfaces.chain import WorkflowLike as _WorkflowLike

ScriptChain: TypeAlias = _WorkflowLike


# ---------------------------------------------------------------------------
# Helper – resolve agent class/object ---------------------------------------
# ---------------------------------------------------------------------------

def _resolve_agent(cfg: PrebuiltAgentConfig) -> Any:  # noqa: ANN401 – dynamic
    """Import *cfg.package* and return the agent object specified by cfg.agent_attr."""

    try:
        mod: ModuleType = importlib.import_module(cfg.package)
    except ModuleNotFoundError as exc:  # pragma: no cover – runtime error path
        raise RuntimeError(f"Cannot import package '{cfg.package}': {exc}") from exc

    attr_name = cfg.agent_attr or cfg.package.split(".")[-1]
    agent_obj = getattr(mod, attr_name, None)
    if agent_obj is None:
        raise RuntimeError(
            f"Attribute '{attr_name}' not found in module '{cfg.package}'."
        )

    return agent_obj


# ---------------------------------------------------------------------------
# Executor implementation ----------------------------------------------------
# ---------------------------------------------------------------------------


@register_node("agent")  # type: ignore[misc,type-var]
async def agent_executor(  # type: ignore[type-var]
    chain: ScriptChain, cfg: PrebuiltAgentConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a *PrebuiltAgentConfig* node."""

    if not isinstance(cfg, PrebuiltAgentConfig):  # defensive – orchestrator bug
        raise TypeError("agent_executor received incompatible cfg type")

    start_ts = datetime.utcnow()

    try:
        agent_cls_or_obj = _resolve_agent(cfg)

        # Instantiate when a class is supplied ---------------------------
        agent_instance: Any
        if callable(agent_cls_or_obj):
            agent_instance = agent_cls_or_obj(**cfg.agent_config)  # type: ignore[arg-type]
        else:
            agent_instance = agent_cls_or_obj

        # Validate before execution (Rule 13) ---------------------------
        if hasattr(agent_instance, "validate"):
            agent_instance.validate()

        # Execute (async-aware) -----------------------------------------
        exec_fn = getattr(agent_instance, "execute", None)
        if exec_fn is None:
            raise AttributeError("Agent object lacks an 'execute' method")

        if asyncio.iscoroutinefunction(exec_fn):
            output = await exec_fn(ctx)
        else:
            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(None, exec_fn, ctx)

        success = True
        error_msg: str | None = None
    except Exception as exc:  # pylint: disable=broad-except
        output = None
        success = False
        error_msg = str(exc)

    end_ts = datetime.utcnow()

    return NodeExecutionResult(  # type: ignore[call-arg]
        success=success,
        error=error_msg,
        output=output,
        metadata=NodeMetadata(
            node_id=cfg.id,
            node_type="agent",
            name=cfg.name,
            start_time=start_ts,
            end_time=end_ts,
        ),
        execution_time=(end_ts - start_ts).total_seconds(),
    ) 