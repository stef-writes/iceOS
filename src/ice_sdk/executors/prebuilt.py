"""Executor for *prebuilt* third-party agents.

Users reference a published/installed package in their chain config::

    {
        "id": "gh_search",
        "type": "prebuilt",
        "package": "ice_agent_ghsearch",
        "agent_attr": "GitHubSearchAgent",
        "model": "gpt-4o"
    }

The executor dynamically imports the target, instantiates the agent, and
executes it in the context of the current ScriptChain.  The resolved object
MUST expose an async ``execute(input: dict) -> NodeExecutionResult | dict``
method or be directly callable.
"""

from __future__ import annotations

import importlib
from datetime import datetime
from types import ModuleType
from typing import Any, Dict

from ice_core.models import NodeMetadata
from ice_sdk.models.node_models import NodeExecutionResult, PrebuiltAgentConfig
from ice_sdk.node_registry import register_node

# Public interface -----------------------------------------------------------
__all__: list[str] = ["prebuilt_executor"]


@register_node("prebuilt")  # type: ignore[misc]
async def prebuilt_executor(
    chain, cfg: PrebuiltAgentConfig, ctx: Dict[str, Any]
):  # noqa: D401
    """Executor for nodes of type ``prebuilt``."""

    start_ts = datetime.utcnow()

    # ------------------------------------------------------------------
    # 1. Dynamically import the target package --------------------------
    # ------------------------------------------------------------------
    try:
        module: ModuleType = importlib.import_module(cfg.package)
    except Exception as exc:  # pragma: no cover – import errors visible to user
        metadata = NodeMetadata(
            node_id=cfg.id, node_type="prebuilt", start_time=start_ts
        )
        return NodeExecutionResult(  # type: ignore[call-arg]
            success=False,
            error=f"Failed importing package '{cfg.package}': {exc}",
            metadata=metadata,
        )

    # Resolve the attribute exporting the agent -------------------------
    agent_attr_name = cfg.agent_attr or "Agent"
    try:
        agent_obj: Any = getattr(module, agent_attr_name)
    except AttributeError as exc:  # pragma: no cover
        metadata = NodeMetadata(
            node_id=cfg.id, node_type="prebuilt", start_time=start_ts
        )
        return NodeExecutionResult(  # type: ignore[call-arg]
            success=False,
            error=f"Package '{cfg.package}' does not export '{agent_attr_name}': {exc}",
            metadata=metadata,
        )

    # Instantiate when object is a class --------------------------------
    if isinstance(agent_obj, type):
        try:
            # Gracefully handle signature (model may be optional) --------
            if cfg.model is not None:
                agent_inst = agent_obj(model=cfg.model)
            else:
                agent_inst = agent_obj()
        except Exception as exc:  # pragma: no cover – constructor error
            metadata = NodeMetadata(
                node_id=cfg.id, node_type="prebuilt", start_time=start_ts
            )
            return NodeExecutionResult(  # type: ignore[call-arg]
                success=False,
                error=f"Could not instantiate '{agent_attr_name}': {exc}",
                metadata=metadata,
            )
    else:
        agent_inst = agent_obj

    # ------------------------------------------------------------------
    # 2. Execute the agent ----------------------------------------------
    # ------------------------------------------------------------------
    try:
        if hasattr(agent_inst, "execute") and callable(getattr(agent_inst, "execute")):
            output = await agent_inst.execute(ctx)
        elif callable(agent_inst):
            output = (
                await agent_inst(ctx) if hasattr(agent_inst, "__call__") else agent_inst
            )
        else:
            raise TypeError(
                "Resolved agent object must be callable or expose an 'execute' coroutine"
            )
    except Exception as exc:  # pragma: no cover – runtime errors surfaced
        metadata = NodeMetadata(
            node_id=cfg.id, node_type="prebuilt", start_time=start_ts
        )
        return NodeExecutionResult(  # type: ignore[call-arg]
            success=False,
            error=str(exc),
            metadata=metadata,
        )

    end_ts = datetime.utcnow()

    metadata = NodeMetadata(
        node_id=cfg.id,
        node_type="prebuilt",
        start_time=start_ts,
        end_time=end_ts,
    )

    # Usage metrics unknown (depends on agent) – leave None -------------
    return NodeExecutionResult(  # type: ignore[call-arg]
        success=True,
        output=output,
        metadata=metadata,
        usage=None,
        execution_time=(end_ts - start_ts).total_seconds(),
    )
