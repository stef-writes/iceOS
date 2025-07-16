from __future__ import annotations

"""Wrapper tool that retries execution of another tool with exponential backoff.

External side-effects (sleep) reside strictly inside ``run`` complying with
repo rule #2.  Backoff uses :pyfunc:`asyncio.sleep` so it never blocks the event
loop.
"""

import asyncio  # noqa: E402
import math  # noqa: E402
from typing import Any, ClassVar, Dict, List  # noqa: E402

from ice_sdk.tools.base import BaseTool, ToolError  # noqa: E402

__all__ = ["RetryWrapperTool"]


class RetryWrapperTool(BaseTool):
    """Retry *inner_tool* up to ``max_attempts`` with exponential backoff."""

    # Static metadata placeholders ------------------------------------------------
    name: ClassVar[str] = "retry_wrapper"
    description: ClassVar[str] = "Retry another tool using exponential backoff."
    tags: ClassVar[List[str]] = ["workflow", "retry", "utility"]

    # ------------------------------------------------------------------
    # Construction ------------------------------------------------------
    # ------------------------------------------------------------------

    def __init__(
        self,
        inner_tool: BaseTool,
        *,
        base_delay: float = 0.25,
        factor: float = 2.0,
        max_attempts: int = 3,
    ) -> None:
        super().__init__()  # initialise BaseModel
        self._tool = inner_tool
        self._base_delay = float(base_delay)
        self._factor = float(factor)
        self._max_attempts = int(max_attempts)

        # Override *instance* metadata to include underlying tool name --------
        self._name = f"retry_{inner_tool.name}"
        self._description = (
            f"Retry wrapper around '{inner_tool.name}' (max_attempts={max_attempts})."
        )

        # Adopt parameter/output schemas from wrapped tool so validation passes
        self.parameters_schema = inner_tool.parameters_schema  # type: ignore[attr-defined]
        self.output_schema = inner_tool.output_schema  # type: ignore[attr-defined]

    # Dynamically expose metadata ---------------------------------------
    @property  # type: ignore[override]
    def name(self) -> str:  # noqa: D401
        return self._name

    @property  # type: ignore[override]
    def description(self) -> str:  # noqa: D401
        return self._description

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        for attempt in range(1, self._max_attempts + 1):
            try:
                return await self._tool.run(**kwargs)
            except Exception:  # noqa: BLE001
                if attempt >= self._max_attempts:
                    raise  # exhaust retries – propagate

                # Compute exponential back-off with jitter (±10%) -------------
                delay = self._base_delay * math.pow(self._factor, attempt - 1)
                jitter = delay * 0.1
                await asyncio.sleep(delay + (jitter * 0.5))

        # Should never reach here --------------------------------------------
        raise ToolError("RetryWrapperTool failed – unexpected fallthrough")
