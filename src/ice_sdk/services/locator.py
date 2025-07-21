"""Service locator and chain execution utilities.

This module was extracted from the legacy ``ice_sdk/services.py`` to resolve a
module–package naming conflict. It provides:

* ``ServiceLocator`` – a minimalist global registry for cross-cutting services.
* ``ChainService``  – a thin wrapper that validates input, tracks cost, and
  executes registered chains asynchronously.

Both classes are re-exported at package level so existing imports
``from ice_sdk.services import ServiceLocator`` continue to work.
"""

from __future__ import annotations

import asyncio
from threading import Lock
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ValidationError

from ice_sdk.providers.costs import CostTracker

__all__: list[str] = [
    "ServiceLocator",
    "ChainService",
    "get_workflow_proto",
]


def get_workflow_proto() -> Type[Any]:
    """Return the *Workflow* concrete class registered by higher layers.

    To respect the onion-architecture boundary, the SDK layer **must not**
    import `ice_orchestrator` directly.  Instead, the concrete implementation
    is provided at runtime by the orchestrator layer via
    :class:`ServiceLocator` under the key ``"workflow_proto"``.

    Raises:
        KeyError: When the orchestrator layer failed to register the workflow
            implementation.  Down-stream callers should catch this and fail
            fast with a helpful message.
    """

    from ice_sdk.services.locator import (
        ServiceLocator,  # local import to avoid circular deps
    )

    return ServiceLocator.get("workflow_proto")


class ChainInput(BaseModel):
    """Validated input schema for chain execution."""

    data: Dict[str, Any]
    runtime: Optional[Dict[str, Any]] = None
    budget: Optional[float] = None


class ChainService:
    """Public interface for chain execution with validation and cost tracking."""

    _chains: Dict[str, Any] = {}
    _cost_tracker = CostTracker()

    # --------------------------------------------------------------------- API
    @classmethod
    def register(cls, chain_id: str, chain: Any) -> None:
        """Register a chain for later execution."""
        cls._chains[chain_id] = chain

    @classmethod
    def _get_chain(cls, chain_id: str) -> Any:
        """Return chain or raise *KeyError* if it is not registered."""
        if chain_id not in cls._chains:
            raise KeyError(f"Chain '{chain_id}' not registered")
        return cls._chains[chain_id]

    @classmethod
    async def execute_async(
        cls, chain_id: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate *input_data*, execute the chain, and return structured result."""
        # Input validation
        try:
            validated_input = ChainInput(data=input_data)
        except ValidationError as exc:
            raise ValueError(f"Invalid chain input: {exc}") from exc

        # Locate chain
        chain = cls._get_chain(chain_id)

        # Reset cost tracking and apply budget if provided
        cls._cost_tracker.reset()
        if validated_input.budget is not None:
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
        except Exception as exc:  # – propagate as runtime
            raise RuntimeError(f"Chain execution failed: {exc}") from exc

    @classmethod
    def execute(cls, chain_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper that blocks until *execute_async* completes."""
        return asyncio.run(cls.execute_async(chain_id, input_data))


class ServiceLocator:  # – simple registry
    """Very small global registry mapping *service names* to instances."""

    _services: Dict[str, Any] = {}
    _lock: Lock = Lock()

    # ------------------------------------------------------------------ API
    @classmethod
    def register(cls, name: str, service: Any) -> None:
        """Register *service* under *name*.

        Overwrites any existing binding – we assume composition-root controls
        lifecycle so this is intentional.
        """
        with cls._lock:
            cls._services[name] = service

    @classmethod
    def get(cls, name: str) -> Any:
        """Return a previously registered service.

        Raises ``KeyError`` if missing – callers should catch and handle.
        """
        try:
            return cls._services[name]
        except KeyError as exc:  # pragma: no cover – programmer error
            raise KeyError(
                f"Service '{name}' not registered in ServiceLocator"
            ) from exc

    @classmethod
    def clear(cls) -> None:  # – test helper
        """Remove **all** registered services (useful in unit tests)."""
        with cls._lock:
            cls._services.clear()
