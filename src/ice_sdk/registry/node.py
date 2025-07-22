"""Runtime registry for node executors.

This is the *canonical* implementation; external code should import
``ice_sdk.registry.node`` or the convenience re-export
``from ice_sdk.registry import NodeRegistry``.

The previous location ``ice_sdk.node_registry`` has been removed.  A thin shim
still exists to emit a DeprecationWarning, but *all* functionality now lives
here so that the old file can be deleted at the next major release.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Protocol, TypeAlias, TypeVar

from ice_sdk.interfaces.chain import ScriptChainLike
from ice_sdk.models.node_models import NodeConfig, NodeExecutionResult

__all__: list[str] = [
    "NodeExecutor",
    "register_node",
    "get_executor",
    "NODE_REGISTRY",
]

# ---------------------------------------------------------------------------
# Public protocol -----------------------------------------------------------
# ---------------------------------------------------------------------------

ScriptChain: TypeAlias = ScriptChainLike


class NodeExecutor(Protocol):
    """Required async call signature for node executors."""

    async def __call__(
        self,
        chain: ScriptChain,
        cfg: NodeConfig,
        ctx: Dict[str, Any],
    ) -> NodeExecutionResult: ...


# ---------------------------------------------------------------------------
# Registry implementation ----------------------------------------------------
# ---------------------------------------------------------------------------

ExecCallable = Callable[
    [ScriptChain, NodeConfig, Dict[str, Any]], Awaitable[NodeExecutionResult]
]
F = TypeVar("F", bound=ExecCallable)

NODE_REGISTRY: Dict[str, ExecCallable] = {}


def register_node(mode: str) -> Callable[[F], F]:
    """Decorator to register *mode* → executor mapping.

    Raises
    ------
    ValueError
        If *mode* is already registered.
    """

    def decorator(func: F) -> F:  # – nested helper
        if mode in NODE_REGISTRY:
            raise ValueError(f"Node mode '{mode}' is already registered")
        NODE_REGISTRY[mode] = func
        return func

    return decorator


def get_executor(mode: str) -> ExecCallable:
    """Return executor for *mode* or raise *KeyError*."""

    try:
        return NODE_REGISTRY[mode]
    except KeyError as exc:  # pragma: no cover – defensive branch
        raise KeyError(
            f"Unknown node mode '{mode}'. Did you forget to import its package?"
        ) from exc


# ---------------------------------------------------------------------------
# Built-in *agent* executor (minimal proxy implementation) -------------------
# ---------------------------------------------------------------------------

from datetime import datetime
import asyncio
import importlib
from types import ModuleType

from ice_core.models import NodeExecutionResult, PrebuiltAgentConfig  # type: ignore


@register_node("agent")  # type: ignore[misc]
async def _agent_executor(  # noqa: D401 – internal helper
    chain: ScriptChain, cfg: NodeConfig, ctx: Dict[str, Any]
) -> NodeExecutionResult:
    """Execute a :class:`~ice_core.models.node_models.PrebuiltAgentConfig` node.

    This in-registry implementation avoids a direct cross-layer import while
    still providing full functionality for test and runtime environments.
    The behaviour is equivalent to *ice_orchestrator.execution.executors.agent*
    but re-implemented locally to respect layering rules.
    """

    # ------------------------------------------------------------------
    # Validate config type ------------------------------------------------
    # ------------------------------------------------------------------
    if not isinstance(cfg, PrebuiltAgentConfig):  # pragma: no cover – defensive
        raise TypeError("_agent_executor received incompatible cfg type")

    start_ts = datetime.utcnow()

    try:
        # --------------------------------------------------------------
        # Dynamically import the user-supplied agent object -------------
        # --------------------------------------------------------------
        try:
            mod: ModuleType = importlib.import_module(cfg.package)
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(f"Cannot import package '{cfg.package}': {exc}") from exc

        attr_name = cfg.agent_attr or cfg.package.split(".")[-1]
        agent_obj = getattr(mod, attr_name, None)
        if agent_obj is None:
            raise RuntimeError(
                f"Attribute '{attr_name}' not found in module '{cfg.package}'."
            )

        # --------------------------------------------------------------
        # Instantiate (if class) and run validate() ---------------------
        # --------------------------------------------------------------
        agent_instance: Any
        if callable(agent_obj):
            agent_instance = agent_obj(**cfg.agent_config)  # type: ignore[arg-type]
        else:
            agent_instance = agent_obj

        if hasattr(agent_instance, "validate"):
            agent_instance.validate()

        # --------------------------------------------------------------
        # Invoke execute() (async-aware) --------------------------------
        # --------------------------------------------------------------
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
        metadata={
            "node_id": cfg.id,
            "node_type": "agent",
            "name": cfg.name,
            "start_time": start_ts,
            "end_time": end_ts,
        },
        execution_time=(end_ts - start_ts).total_seconds(),
    )
