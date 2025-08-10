"""Core protocol definitions for iceOS.

This package contains all abstract interfaces and protocols that define
contracts between layers. No implementations should be in this package.

Layer Rules:
1. NO external dependencies (pure Python only)
2. NO I/O operations
3. Define contracts only, no implementations
"""

from typing import Any, Set

from .agent import IAgent
from .embedder import IEmbedder
from .executor import IExecutor
from .llm import ILLMProvider, LLMProviderRegistry, llm_provider_registry
from .node import INode
from .registry import IRegistry
from .tool import ITool
from .vector import IVectorIndex
from .workflow import IWorkflow

# validated_protocol will be imported lazily at the end to avoid circulars


# ---------------------------------------------------------------------------
# Protocol enforcement utilities
# ---------------------------------------------------------------------------

ENFORCED_PROTOCOLS = {
    "node": INode,
    "tool": ITool,
    "registry": IRegistry,
    "vector": IVectorIndex,
    "embedder": IEmbedder,
    "workflow": IWorkflow,
    "llm": ILLMProvider,
    "agent": IAgent,
    "executor": IExecutor,
}


def _missing_abstracts(cls: type, proto: type) -> Set[str]:
    """Return the set of abstract attributes *proto* requires that *cls* lacks."""
    abstract_attrs: Set[str] = getattr(proto, "__abstractmethods__", set())  # type: ignore[attr-defined]
    return {name for name in abstract_attrs if not hasattr(cls, name)}


def enforce_protocol(protocol: type) -> Any:  # pragma: no cover – utility
    """Class decorator that enforces *protocol* implementation at import-time.

    Raises:
        TypeError: If the decorated class does not implement *protocol*.
    """

    def decorator(cls: type) -> type:
        # Skip validation for abstract classes – they can remain incomplete.
        if getattr(cls, "__isabstractmethod__", False):  # type: ignore[attr-defined]
            return cls

        if not issubclass(cls, protocol):  # pyright: ignore[reportArgumentType]
            missing = _missing_abstracts(cls, protocol)
            raise TypeError(
                f"{cls.__qualname__} does not implement required protocol "
                f"{protocol.__qualname__}; missing: {sorted(missing)}"
            )
        return cls

    return decorator


from .validation import validated_protocol  # noqa: E402  (import late)

__all__ = [
    "INode",
    "ITool",
    "IRegistry",
    "IVectorIndex",
    "IEmbedder",
    "IWorkflow",
    "ILLMProvider",
    "LLMProviderRegistry",
    "llm_provider_registry",
    "ENFORCED_PROTOCOLS",
    "enforce_protocol",
    "IAgent",
    "IExecutor",
    "validated_protocol",
]
