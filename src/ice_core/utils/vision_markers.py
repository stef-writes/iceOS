"""Vision Architecture Markers

Simple decorators to document which tier of the iceOS vision each component serves.
This makes the codebase self-documenting about architectural intent.

The Three Tiers:
1. Frosty (Interpreter) - Natural language → Blueprint
2. MCP API (Compiler) - Blueprint validation & optimization  
3. DAG Orchestrator (Runtime) - Deterministic execution
"""

from typing import Callable, TypeVar

T = TypeVar("T")


def frosty_tier(purpose: str) -> Callable[[T], T]:
    """Mark component as part of Frosty interpreter tier.

    Example:
        @frosty_tier("Translates natural language to tool config")
        class ToolInterpreter:
            pass
    """

    def decorator(cls: T) -> T:
        cls.__vision_tier__ = "frosty"  # type: ignore
        cls.__vision_purpose__ = purpose  # type: ignore
        return cls

    return decorator


def mcp_tier(purpose: str) -> Callable[[T], T]:
    """Mark component as part of MCP API compiler tier.

    Example:
        @mcp_tier("Validates and optimizes workflow blueprints")
        class BlueprintValidator:
            pass
    """

    def decorator(cls: T) -> T:
        cls.__vision_tier__ = "mcp"  # type: ignore
        cls.__vision_purpose__ = purpose  # type: ignore
        return cls

    return decorator


def runtime_tier(purpose: str) -> Callable[[T], T]:
    """Mark component as part of DAG orchestrator runtime tier.

    Example:
        @runtime_tier("Executes nodes with retry and error handling")
        class NodeExecutor:
            pass
    """

    def decorator(cls: T) -> T:
        cls.__vision_tier__ = "runtime"  # type: ignore
        cls.__vision_purpose__ = purpose  # type: ignore
        return cls

    return decorator


def multi_granularity(level: str) -> Callable[[T], T]:
    """Mark component as supporting multi-level translation.

    Levels: tool, node, chain, workflow

    Example:
        @multi_granularity("node")
        class LLMNodeConfig:
            pass
    """

    def decorator(cls: T) -> T:
        cls.__granularity_level__ = level  # type: ignore
        return cls

    return decorator
