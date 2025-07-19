from __future__ import annotations

import asyncio
import math
from typing import Any, Dict

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["RetryWrapperSkill"]


class RetryWrapperSkill(SkillBase):
    """Retry another *Skill* up to *max_attempts* with exponential backoff."""

    name: str = "retry_wrapper"
    description: str = "Retry another skill using exponential backoff."

    def __init__(
        self,
        inner_skill: SkillBase,
        *,
        base_delay: float = 0.25,
        factor: float = 2.0,
        max_attempts: int = 3,
    ):
        super().__init__()
        self._skill = inner_skill
        self._base_delay = base_delay
        self._factor = factor
        self._max_attempts = max_attempts
        self.name = f"retry_{inner_skill.name}"  # type: ignore[assignment]
        self.description = f"Retry wrapper around '{inner_skill.name}'."

    def get_required_config(self):
        return []

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        """Retry the wrapped skill with exponential backoff.

        Accepts arbitrary kwargs and forwards them verbatim to the *inner* skill.
        """

        for attempt in range(1, self._max_attempts + 1):
            try:
                return await self._skill.execute(kwargs)
            except Exception:  # noqa: BLE001
                if attempt >= self._max_attempts:
                    raise
                delay = self._base_delay * math.pow(self._factor, attempt - 1)
                jitter = delay * 0.1
                await asyncio.sleep(delay + (jitter * 0.5))
        raise SkillExecutionError("RetryWrapperSkill exhausted attempts")
