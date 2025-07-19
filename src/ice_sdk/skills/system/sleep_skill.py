from __future__ import annotations

import asyncio
from typing import Any, Dict

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["SleepSkill"]


class SleepSkill(SkillBase):
    """Pause execution for a number of seconds (\<=60)."""

    name: str = "sleep"
    description: str = "Pause execution for a number of seconds"
    tags = ["utility", "time"]

    def get_required_config(self) -> list[str]:  # noqa: D401
        return []

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        seconds = kwargs.get("seconds")
        if not isinstance(seconds, (int, float)):
            raise SkillExecutionError("'seconds' must be a number")
        if seconds < 0 or seconds > 60:
            raise SkillExecutionError("'seconds' must be between 0 and 60")

        await asyncio.sleep(float(seconds))
        return {"slept": float(seconds)}
