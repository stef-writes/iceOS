"""Runtime facade around ice_sdk Skill registry for low-code consumers.

API (sync wrappers) ---------------------------------------------------------
    register(name: str, skill_cls: type[SkillBase]) -> bool
    execute(name: str, inputs: dict) -> dict

The gateway delegates to *ice_sdk.skills.global_skill_registry* but hides
Pydantic/async details so that CLI or HTTP handlers can work with plain
Python dicts.

On import we register an instance in ServiceLocator under key
``"skill_gateway"``.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Mapping, Type

from pydantic import BaseModel, ValidationError

from ice_sdk.services import ServiceLocator
from ice_sdk.skills.base import SkillBase
from ice_sdk.skills.registry import SkillRegistrationError, global_skill_registry

__all__: list[str] = ["SkillGateway", "SkillExecutionRequest"]


class SkillExecutionRequest(BaseModel):
    skill_name: str
    inputs: Dict[str, Any]


class SkillGateway:
    """Thin orchestrator-layer gateway around Skill registry."""

    # ------------------------------------------------------------------
    # Registration ------------------------------------------------------
    # ------------------------------------------------------------------
    def register(self, name: str, skill_cls: Type[SkillBase]) -> bool:  # noqa: D401
        try:
            global_skill_registry.register(name, skill_cls())  # type: ignore[arg-type]
            return True
        except SkillRegistrationError as exc:
            raise ValueError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Execution ---------------------------------------------------------
    # ------------------------------------------------------------------
    async def _execute_async(self, req: SkillExecutionRequest) -> Any:  # noqa: ANN401
        return await global_skill_registry.execute(req.skill_name, req.inputs)

    def execute(
        self, skill_name: str, inputs: Mapping[str, Any]
    ) -> Any:  # noqa: D401 ANN401
        """Sync helper that validates inputs then runs the Skill."""
        try:
            req = SkillExecutionRequest(skill_name=skill_name, inputs=dict(inputs))
        except ValidationError as err:
            raise ValueError(str(err)) from err

        return asyncio.run(self._execute_async(req))


# ----------------------------------------------------------------------
# Auto-register in ServiceLocator for easy discovery
# ----------------------------------------------------------------------
ServiceLocator.register("skill_gateway", SkillGateway())
