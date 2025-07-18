from __future__ import annotations

import asyncio
from typing import Any, Dict

from ..base import SkillBase
from ...utils.errors import SkillExecutionError

__all__ = ["SleepSkill"]


class SleepSkill(SkillBase):
    """Pause execution for a number of seconds (\<=60)."""

    name: str = "sleep"
    description: str = "Pause execution for a number of seconds"
    tags = ["utility", "time"]

    def get_required_config(self):  # noqa: D401
        return []

    async def _execute_impl(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        seconds_raw = input_data.get("seconds", 0)
        try:
            seconds = float(seconds_raw)
        except Exception as exc:  # noqa: BLE001
            raise SkillExecutionError("'seconds' must be a number") from exc

        if seconds < 0 or seconds > 60:
            raise SkillExecutionError("'seconds' must be between 0 and 60")

        await asyncio.sleep(seconds)
        return {"slept": seconds} 