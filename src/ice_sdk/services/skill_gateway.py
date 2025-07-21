"""SkillGateway – runtime facade around SDK Skill registry.

Relocated from *ice_core.services* to *ice_sdk.services* to respect layer
boundaries (core must not depend on sdk).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Mapping, Type

from pydantic import BaseModel, ValidationError

from ice_sdk.registry.skill import SkillRegistrationError, global_skill_registry
from ice_sdk.services.locator import ServiceLocator
from ice_sdk.skills.base import SkillBase

__all__: list[str] = ["SkillGateway", "SkillExecutionRequest"]


class SkillExecutionRequest(BaseModel):
    skill_name: str
    inputs: Dict[str, Any]


class SkillGateway:
    """Thin gateway around `global_skill_registry` with sync helpers."""

    def register(self, name: str, skill_cls: Type[SkillBase]) -> bool:  # noqa: D401
        try:
            global_skill_registry.register(name, skill_cls())  # type: ignore[arg-type]
            return True
        except SkillRegistrationError as exc:
            raise ValueError(str(exc)) from exc

    async def _execute_async(self, req: SkillExecutionRequest) -> Any:
        return await global_skill_registry.execute(req.skill_name, req.inputs)

    def execute(
        self, skill_name: str, inputs: Mapping[str, Any]
    ) -> Any:  # noqa: D401 ANN401
        try:
            req = SkillExecutionRequest(skill_name=skill_name, inputs=dict(inputs))
        except ValidationError as err:
            raise ValueError(str(err)) from err

        return asyncio.run(self._execute_async(req))


# Auto-register -------------------------------------------------------------
ServiceLocator.register("skill_gateway", SkillGateway())
