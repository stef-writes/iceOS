from __future__ import annotations

import asyncio
import importlib
import inspect
from typing import Any, Dict

from pydantic import BaseModel

from ice_sdk.registry.unit import global_unit_registry


class UnitRequest(BaseModel):
    unit_name: str
    inputs: Dict[str, Any]


class UnitService:
    _registry: Dict[str, Any] = {}

    def __init__(self) -> None:
        # Snapshot
        for name, unit in global_unit_registry:
            self._registry.setdefault(name, unit)

        # Entry-points
        try:
            from importlib.metadata import entry_points

            for ep in entry_points(group="ice_sdk.units"):
                try:
                    loaded = ep.load()
                    if inspect.isclass(loaded):
                        loaded = loaded()
                    name = getattr(loaded, "name", ep.name)
                    self._registry.setdefault(name, loaded)
                except Exception:
                    continue
        except Exception:
            pass

        # Fallback scan (optional minimal) – skip for brevity

    def available_units(self) -> list[str]:
        return sorted(self._registry.keys())

    async def execute(self, request: UnitRequest):
        unit = self._registry.get(request.unit_name)
        if unit is None:
            try:
                unit = global_unit_registry.get(request.unit_name)
                self._registry[request.unit_name] = unit
            except Exception as exc:
                raise ValueError(f"Unit '{request.unit_name}' not registered") from exc
        exec_fn = getattr(unit, "execute")
        if inspect.iscoroutinefunction(exec_fn):
            return await exec_fn(request.inputs)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, exec_fn, request.inputs) 