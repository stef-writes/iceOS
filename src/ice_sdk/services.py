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

import asyncio
from threading import Lock
from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError

from ice_sdk.providers.costs import CostTracker

__all__: list[str] = ["ServiceLocator", "ChainService"]


class ChainInput(BaseModel):
    """Validated input for chain execution"""

    data: Dict[str, Any]
    runtime: Optional[Dict[str, Any]] = None
    budget: Optional[float] = None


class ChainService:
    """Public interface for chain execution with validation and cost tracking"""

    _chains: Dict[str, Any] = {}
    _cost_tracker = CostTracker()

    @classmethod
    def register(cls, chain_id: str, chain: Any) -> None:
        """Register a chain for execution"""
        cls._chains[chain_id] = chain

    @classmethod
    def _get_chain(cls, chain_id: str) -> Any:
        """Get registered chain or raise KeyError"""
        if chain_id not in cls._chains:
            raise KeyError(f"Chain '{chain_id}' not registered")
        return cls._chains[chain_id]

    @classmethod
    async def execute_async(
        cls, chain_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Async execution with validation and cost tracking"""
        # Input validation
        try:
            validated_input = ChainInput(data=input_data)
        except ValidationError as e:
            raise ValueError(f"Invalid chain input: {e}")

        # Get chain
        chain = cls._get_chain(chain_id)

        # Reset cost tracking
        cls._cost_tracker.reset()

        # Execute with budget enforcement
        if validated_input.budget:
            cls._cost_tracker.set_budget(validated_input.budget)

        try:
            result = await chain.execute_async(validated_input.data)
            return {
                "result": result,
                "costs": cls._cost_tracker.get_costs(),
                "metadata": {
                    "chain_id": chain_id,
                    "execution_time": cls._cost_tracker.get_execution_time(),
                },
            }
        except Exception as e:
            raise RuntimeError(f"Chain execution failed: {str(e)}")

    @classmethod
    def execute(cls, chain_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for async execution"""
        return asyncio.run(cls.execute_async(chain_id, input_data))


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
