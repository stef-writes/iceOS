"""Global service registry for iceOS.

This lightweight *service locator* lets top-level application code register
shared singleton-like services (logging, config, ToolService, etc.) that
other parts of the codebase can access **without** importing higher-level
modules directly, keeping layer boundaries intact.

Usage (composition-root)::

    from ice_sdk.tools.service import ToolService
    from ice_sdk.context import GraphContextManager
    from ice_sdk.services import ServiceLocator

    tool_service = ToolService()
    ctx_manager = GraphContextManager()

    ServiceLocator.register("tool_service", tool_service)
    ServiceLocator.register("context_manager", ctx_manager)

Somewhere else::

    from ice_sdk.services import ServiceLocator

    tool_service = ServiceLocator.get("tool_service")

Notes
-----
* Keep the registry minimal – it should only store **cross-cutting** shared
  services that would otherwise create circular dependencies.
* Regular business-logic dependencies should still be passed explicitly via
  constructor injection.
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Dict

__all__: list[str] = ["ServiceLocator"]


class ServiceLocator:  # noqa: D401 – simple registry
    """Very small global registry mapping *service names* to instances."""

    _services: Dict[str, Any] = {}
    _lock: Lock = Lock()

    # ------------------------------------------------------------------ API
    @classmethod
    def register(cls, name: str, service: Any) -> None:  # noqa: D401
        """Register *service* under *name*.

        Overwrites any existing binding – we assume composition-root controls
        lifecycle so this is intentional.
        """
        with cls._lock:
            cls._services[name] = service

    @classmethod
    def get(cls, name: str) -> Any:  # noqa: D401
        """Return service previously registered under *name*.

        Raises ``KeyError`` if missing – callers should catch and handle.
        """
        try:
            return cls._services[name]
        except KeyError as exc:  # pragma: no cover – programmer error
            raise KeyError(
                f"Service '{name}' not registered in ServiceLocator"
            ) from exc

    @classmethod
    def clear(cls) -> None:  # noqa: D401 – test helper
        """Remove **all** registered services (useful in unit tests)."""
        with cls._lock:
            cls._services.clear()
