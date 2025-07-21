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
    ) -> NodeExecutionResult:  # noqa: D401
        ...


# ---------------------------------------------------------------------------
# Registry implementation ----------------------------------------------------
# ---------------------------------------------------------------------------

ExecCallable = Callable[
    [ScriptChain, NodeConfig, Dict[str, Any]], Awaitable[NodeExecutionResult]
]
F = TypeVar("F", bound=ExecCallable)

NODE_REGISTRY: Dict[str, ExecCallable] = {}


def register_node(mode: str) -> Callable[[F], F]:  # noqa: D401
    """Decorator to register *mode* → executor mapping.

    Raises
    ------
    ValueError
        If *mode* is already registered.
    """

    def decorator(func: F) -> F:  # noqa: D401 – nested helper
        if mode in NODE_REGISTRY:
            raise ValueError(f"Node mode '{mode}' is already registered")
        NODE_REGISTRY[mode] = func
        return func

    return decorator


def get_executor(mode: str) -> ExecCallable:  # noqa: D401
    """Return executor for *mode* or raise *KeyError*."""

    try:
        return NODE_REGISTRY[mode]
    except KeyError as exc:  # pragma: no cover – defensive branch
        raise KeyError(
            f"Unknown node mode '{mode}'. Did you forget to import its package?"
        ) from exc
