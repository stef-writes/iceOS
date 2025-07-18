from __future__ import annotations

import asyncio
import base64
import io
from typing import Any, Dict, List, Tuple

from pydantic import ConfigDict

from ..base import SkillBase
from ...utils.errors import SkillExecutionError

__all__ = ["ComputerSkill"]


class ComputerSkill(SkillBase):
    """Control a virtual computer via *pyautogui* (click, type, scroll, screenshot)."""

    name: str = "computer"
    description: str = "Control a virtual computer"
    tags: List[str] = ["automation", "ui", "system"]

    # Accept custom screen dimensions via instance __init__ -------------------
    model_config = ConfigDict(extra="allow")  # type: ignore[var-annotated]

    def __init__(self, dimensions: Tuple[int, int] | None = None):  # noqa: D401
        super().__init__()
        self.dimensions = dimensions or (1280, 720)

    def get_required_config(self):  # noqa: D401
        return []

    async def _execute_impl(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action")
        if action not in {"click", "type", "scroll", "screenshot"}:
            raise SkillExecutionError("Unsupported action for computer skill")

        try:
            import pyautogui  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise SkillExecutionError("'pyautogui' package is required for ComputerSkill") from exc

        try:
            if action == "click":
                x = input_data.get("x")
                y = input_data.get("y")
                if x is None or y is None:
                    raise SkillExecutionError("'click' requires 'x' and 'y'")
                await asyncio.to_thread(pyautogui.click, x, y)  # type: ignore[arg-type]
                return {"success": True}

            if action == "type":
                text = input_data.get("text")
                if text is None:
                    raise SkillExecutionError("'type' requires 'text'")
                await asyncio.to_thread(pyautogui.typewrite, str(text))  # type: ignore[arg-type]
                return {"success": True}

            if action == "scroll":
                x = input_data.get("x", 0)
                y = input_data.get("y")
                if y is None:
                    raise SkillExecutionError("'scroll' requires 'y' delta")
                await asyncio.to_thread(pyautogui.scroll, y, x=x)  # type: ignore[arg-type]
                return {"success": True}

            if action == "screenshot":
                img = await asyncio.to_thread(pyautogui.screenshot)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode()
                return {"image_base64": encoded}
        except Exception as exc:  # pragma: no cover
            raise SkillExecutionError(f"Computer action failed: {exc}") from exc

        return {"success": False} 