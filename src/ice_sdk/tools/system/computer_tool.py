from __future__ import annotations

import asyncio
import base64
import io
from typing import Any, Dict, List, Tuple

from pydantic import ConfigDict

from ...utils.errors import ToolExecutionError
from ..base import ToolBase

__all__ = ["ComputerTool"]

class ComputerTool(ToolBase):
    """Control a virtual computer via *pyautogui* (click, type, scroll, screenshot)."""

    name: str = "computer"
    description: str = "Control a virtual computer"
    tags: List[str] = ["automation", "ui", "system"]

    # Accept custom screen dimensions via instance __init__ -------------------
    model_config = ConfigDict(extra="allow")  # type: ignore[var-annotated]

    def __init__(self, dimensions: Tuple[int, int] | None = None):
        super().__init__()
        # Bypass Pydantic attribute validation for runtime-only data
        object.__setattr__(self, "dimensions", dimensions or (1280, 720))

    def get_required_config(self) -> list[str]:
        return []

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        input_data: Dict[str, Any] = kwargs.get("input_data", kwargs)
        action = input_data.get("action")
        if action not in {"click", "type", "scroll", "screenshot"}:
            raise ToolExecutionError("computer", "Unsupported action for computer tool")

        try:
            import pyautogui  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ToolExecutionError(
                "'pyautogui' package is required for ComputerTool"
            ) from exc

        try:
            if action == "click":
                x = input_data.get("x")
                y = input_data.get("y")
                if x is None or y is None:
                    raise ToolExecutionError("computer", "'click' requires 'x' and 'y'")
                await asyncio.to_thread(pyautogui.click, x, y)  # type: ignore[arg-type]
                return {"success": True}

            if action == "type":
                text = input_data.get("text")
                if text is None:
                    raise ToolExecutionError("computer", "'type' requires 'text'")
                await asyncio.to_thread(pyautogui.typewrite, str(text))  # type: ignore[arg-type]
                return {"success": True}

            if action == "scroll":
                x = input_data.get("x", 0)
                y = input_data.get("y")
                if y is None:
                    raise ToolExecutionError("computer", "'scroll' requires 'y' delta")
                await asyncio.to_thread(pyautogui.scroll, y, x=x)  # type: ignore[arg-type]
                return {"success": True}

            if action == "screenshot":
                img = await asyncio.to_thread(pyautogui.screenshot)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode()
                return {"image_base64": encoded}
        except Exception as exc:  # pragma: no cover
            raise ToolExecutionError("computer", f"Computer action failed: {exc}") from exc

        return {"success": False}
