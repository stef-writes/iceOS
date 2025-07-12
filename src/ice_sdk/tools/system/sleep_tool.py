"""Sleep tool for pausing execution."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Dict, List

from ..base import BaseTool, ToolError


class SleepTool(BaseTool):
    """Pause execution for *n* seconds.

    Useful for demo workflows that need to simulate latency or rate-limit.
    """

    name: ClassVar[str] = "sleep"
    description: ClassVar[str] = "Pause execution for a number of seconds"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "seconds": {
                "type": "number",
                "minimum": 0,
                "maximum": 60,
                "description": "Duration of the sleep in seconds (max 60)",
            }
        },
        "required": ["seconds"],
    }
    # Capability taxonomy -------------------------------------------------
    tags: ClassVar[List[str]] = ["utility", "time"]

    # Explicit output schema ---------------------------------------------
    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "slept": {
                "type": "number",
                "description": "Duration the tool paused in seconds",
            }
        },
        "required": ["slept"],
    }

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        seconds_raw = kwargs.get("seconds", 0)
        try:
            seconds = float(seconds_raw)
        except Exception as exc:  # noqa: BLE001 – invalid cast
            raise ToolError("'seconds' must be a number") from exc

        if seconds < 0 or seconds > 60:
            raise ToolError("'seconds' must be between 0 and 60")

        await asyncio.sleep(seconds)
        return {"slept": seconds}
