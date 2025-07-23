from __future__ import annotations

"""Unit registry – catalogue of reusable LLM+Tool composites ("units")."""

from typing import Any, Dict, Generator, Mapping, Tuple
import warnings

from pydantic import BaseModel, PrivateAttr

__all__: list[str] = ["UnitRegistry", "global_unit_registry"]


class UnitRegistrationError(RuntimeError):
    """Raised when a unit cannot be registered."""


class UnitRegistry(BaseModel):
    """In-memory registry mapping *unit.name* → instantiated unit object."""

    _units: Dict[str, Any] = PrivateAttr(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True, "extra": "forbid"}

    # ------------------------------------------------------------------ API
    def register(self, name: str, unit: Any) -> None:
        if name in self._units:
            raise UnitRegistrationError(f"Unit '{name}' already registered")

        validate_fn = getattr(unit, "validate", None)
        if callable(validate_fn):
            validate_fn()

        self._units[name] = unit

    def get(self, name: str) -> Any:
        try:
            return self._units[name]
        except KeyError as exc:
            raise UnitRegistrationError(f"Unit '{name}' not found") from exc

    async def execute(self, name: str, payload: Mapping[str, Any]) -> Any:
        unit = self.get(name)
        exec_fn = getattr(unit, "execute")
        import asyncio
        if asyncio.iscoroutinefunction(exec_fn):
            return await exec_fn(payload)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, exec_fn, payload)

    # ------------------------------------------------------------------ helpers
    def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
        yield from self._units.items()

    def __len__(self) -> int:  # pragma: no cover
        return len(self._units)


global_unit_registry: "UnitRegistry[Any]" = UnitRegistry()  # type: ignore[type-var]

# Shim
import sys as _sys
_sys.modules.setdefault("ice_sdk.registry.units", _sys.modules[__name__])

warnings.warn(
    "'global_unit_registry' has moved to 'ice_sdk.registry.unit'.",
    DeprecationWarning,
    stacklevel=2,
) 