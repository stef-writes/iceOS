from __future__ import annotations

import asyncio
from typing import Any, Dict

from ..base import ToolBase

__all__ = ["SleepTool"]

class SleepTool(ToolBase):
    """Sleep for a specified number of seconds."""

    name: str = "sleep"
    description: str = "Sleep for a specified number of seconds"

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        seconds = kwargs.get("seconds", 1)
        await asyncio.sleep(float(seconds))
        return {"slept_for": float(seconds)}
