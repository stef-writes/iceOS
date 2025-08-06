from __future__ import annotations

"""Factory-centric helpers for tool authoring & workflow sugar.

This module introduces symmetry with the *agent* factory pattern:

* ``@tool_factory`` – decorator for registering a factory function that returns a
  *new* instance of a `ToolBase` subclass each call.  The decorator derives and
  registers the import path automatically, so call-sites only need the public
  *name*.
* ``tool_node`` – tiny helper returning a fully-typed `ToolNodeConfig` that
  references a *factory* (not a singleton).  It can be appended directly to a
  `WorkflowBuilder` or used wherever a `NodeConfig` is accepted.

Both helpers obey iceOS rules:
• strict typing & Pydantic models
• no side-effects outside the registry registration performed by the decorator
"""

from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from pydantic import validate_call

from ice_core.base_tool import ToolBase
from ice_core.models import ToolNodeConfig
from ice_core.unified_registry import register_tool_factory

__all__: list[str] = [
    "tool_factory",
    "tool_node",
]

TToolFactory = TypeVar("TToolFactory", bound=Callable[..., ToolBase])


def tool_factory(
    name: Optional[str] = None,
    *,
    auto_register: bool = True,
) -> Callable[[TToolFactory], TToolFactory]:
    """Decorator to mark *factory functions* that build tools.

    Parameters
    ----------
    name : str | None
        Public registry name (defaults to the function name).
    auto_register : bool, default ``True``
        Whether to auto-register the factory with the global registry when the
        module is imported.  Keep ``True`` for production code; set to ``False``
        in tests that verify registration logic manually.

    Returns
    -------
    Callable[[TToolFactory], TToolFactory]
        The original factory function, unmodified (besides validation wrapper).
    """

    def decorator(factory: TToolFactory) -> TToolFactory:  # type: ignore[name-defined]
        public_name = name or factory.__name__

        if auto_register:
            import_path = f"{factory.__module__}:{factory.__name__}"
            register_tool_factory(public_name, import_path)

        # Attach metadata for introspection / tooling
        setattr(factory, "__tool_factory_name__", public_name)
        setattr(factory, "__tool_factory_registered__", auto_register)

        # Optional runtime arg validation via pydantic.validate_call
        validated_factory = validate_call(factory)  # type: ignore[arg-type]
        return wraps(factory)(validated_factory)  # type: ignore[return-value]

    return decorator


def tool_node(
    node_id: str,
    *,
    factory: str,
    tool_args: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> ToolNodeConfig:
    """Convenience helper that returns a `ToolNodeConfig` referencing a *factory*.

    Example
    -------
    >>> from ice_builder.utils.tool_factory import tool_node
    >>> tn = tool_node("price_calc", factory="pricing_price_calculator", margin=0.15)
    """

    return ToolNodeConfig(
        id=node_id,
        tool_name=factory,
        tool_args=tool_args or {k: v for k, v in extra.items()},
        name=factory,
    )
