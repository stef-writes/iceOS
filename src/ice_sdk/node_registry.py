# ruff: noqa: E402
from __future__ import annotations

"""Global registry for mapping *node modes* (string discriminator from the config)
→ to async *executor callables* used by :pyclass:`~ice_orchestrator.script_chain.ScriptChain`.

The registry enables plug-in style extension: any package can register a new
node type by importing :pyfunc:`register_node` at import-time.  No further
changes to the orchestrator are required.

Executor signature  ---------------------------------------------------------
```
async def executor(chain: ScriptChain, cfg: NodeConfig, ctx: dict[str, Any]) -> NodeExecutionResult
```
* **chain** – the calling :class:`ScriptChain` instance.  Gives access to
  context manager, metrics helpers, etc.
* **cfg**   – the *NodeConfig* instance for the node being executed.
* **ctx**   – input data already prepared by the orchestrator.

The executor returns a fully-populated :class:`NodeExecutionResult`.

See :pymod:`ice_sdk.executors.builtin` for the built-in *ai* and *tool* modes.
"""

from typing import Any, Callable, Dict, Protocol, TypeAlias, TypeVar

from ice_sdk.interfaces.chain import ScriptChainLike

ScriptChain: TypeAlias = ScriptChainLike

from ice_sdk.models.node_models import (  # noqa: F401 – re-exported for Protocol
    NodeConfig,
    NodeExecutionResult,
)

__all__ = [
    "NodeExecutor",
    "register_node",
    "get_executor",
    "NODE_REGISTRY",
]


class NodeExecutor(Protocol):
    """Required call signature for node executors."""

    async def __call__(
        self,
        chain: ScriptChain,
        cfg: NodeConfig,
        ctx: Dict[str, Any],
    ) -> NodeExecutionResult:  # noqa: D401
        ...


# Registry of mode → executor callable ------------------------------------------------

ExecCallable = Callable[[ScriptChain, NodeConfig, Dict[str, Any]], NodeExecutionResult]

F = TypeVar("F", bound=ExecCallable)

NODE_REGISTRY: Dict[str, ExecCallable] = {}


def register_node(mode: str) -> Callable[[F], F]:  # noqa: D401
    """Decorator to register a new *node mode* executor.

    Example
    -------
    >>> @register_node("my_custom")
    ... async def executor(chain, cfg, ctx):
    ...     return await do_something(cfg, ctx)
    """

    def decorator(func: F) -> F:
        if mode in NODE_REGISTRY:
            raise ValueError(f"Node mode '{mode}' is already registered")
        NODE_REGISTRY[mode] = func
        return func

    return decorator


def get_executor(mode: str) -> ExecCallable:  # noqa: D401
    """Return the executor registered for *mode* or raise *KeyError*."""

    try:
        return NODE_REGISTRY[mode]
    except KeyError as exc:  # pragma: no cover – defensive branch
        raise KeyError(
            f"Unknown node mode '{mode}'. Did you forget to import its package?"
        ) from exc
