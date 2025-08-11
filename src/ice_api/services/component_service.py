from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, Optional, Tuple

from ice_api.services.component_repo import ComponentRepository, _hash_lock
from ice_core.models.mcp import ComponentDefinition, ComponentValidationResult
from ice_core.validation.component_validator import validate_component


class ComponentService:
    def __init__(self, repo: ComponentRepository) -> None:
        self._repo = repo

    async def validate(
        self, definition: ComponentDefinition
    ) -> ComponentValidationResult:
        return await validate_component(definition)

    async def register(
        self, definition: ComponentDefinition
    ) -> Tuple[ComponentValidationResult, Optional[str]]:
        result = await self.validate(definition)
        if not result.valid:
            return result, None

        # Load existing for version bump semantics
        existing, prev_lock = await self._repo.get(definition.type, definition.name)
        version = (
            (int(existing.get("version", 1)) + 1) if isinstance(existing, dict) else 1
        )

        record = {
            "definition": definition.model_dump(mode="json"),
            "created_at": (
                existing.get("created_at")
                if isinstance(existing, dict)
                else _dt.datetime.utcnow().isoformat()
            ),
            "updated_at": _dt.datetime.utcnow().isoformat(),
            "version": version,
        }
        lock = _hash_lock(record)
        if prev_lock and str(prev_lock) == lock:
            await self._repo.set_index(f"{definition.type}:{definition.name}", lock)
            return result, lock

        await self._repo.put(definition.type, definition.name, record, lock)
        await self._repo.set_index(f"{definition.type}:{definition.name}", lock)
        return result, lock

    async def get(
        self, component_type: str, name: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return await self._repo.get(component_type, name)

    async def list_index(self) -> Dict[str, str]:
        return await self._repo.get_index()
