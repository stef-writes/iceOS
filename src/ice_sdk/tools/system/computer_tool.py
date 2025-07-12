"""Computer automation tool for UI control."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Dict, List

from pydantic import ConfigDict

from ..base import BaseTool, ToolError


class ComputerTool(BaseTool):
    """Tool for controlling a virtual computer."""

    name: ClassVar[str] = "computer"
    description: ClassVar[str] = "Control a virtual computer"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["click", "type", "scroll", "screenshot"],
                "description": "Action to perform",
            },
            "x": {"type": "integer", "description": "X coordinate for click/scroll"},
            "y": {"type": "integer", "description": "Y coordinate for click/scroll"},
            "text": {"type": "string", "description": "Text to type"},
        },
        "required": ["action"],
    }

    # Allow dynamic attribute assignment (e.g. self.dimensions)
    model_config = ConfigDict(extra="allow")  # type: ignore[var-annotated]

    def __init__(self, dimensions: tuple[int, int] = (1280, 720)):
        """Initialize computer tool.

        Args:
            dimensions: Screen dimensions (width, height)
        """
        super().__init__()
        self.dimensions = dimensions

    tags: ClassVar[List[str]] = ["automation", "ui", "system"]

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "image_base64": {"type": "string"},
        },
        "required": ["success"],
    }

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        """Execute computer action.

        Args:
            action: Action to perform
            x: X coordinate
            y: Y coordinate
            text: Text to type
        """
        import base64
        import io

        action = kwargs.get("action")
        if action not in {"click", "type", "scroll", "screenshot"}:
            raise ToolError("Unsupported action for computer tool")

        try:
            import pyautogui  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ToolError("'pyautogui' package is required for ComputerTool") from exc

        try:
            if action == "click":
                x = kwargs.get("x")
                y = kwargs.get("y")
                if x is None or y is None:
                    raise ToolError("'click' requires 'x' and 'y' coordinates")
                await asyncio.to_thread(pyautogui.click, x, y)  # type: ignore[arg-type]
                return {"success": True}

            if action == "type":
                text = kwargs.get("text")
                if text is None:
                    raise ToolError("'type' requires 'text'")
                await asyncio.to_thread(pyautogui.typewrite, str(text))  # type: ignore[arg-type]
                return {"success": True}

            if action == "scroll":
                x = kwargs.get("x", 0)
                y = kwargs.get("y")
                if y is None:
                    raise ToolError("'scroll' requires 'y' delta")
                await asyncio.to_thread(pyautogui.scroll, y, x=x)  # type: ignore[arg-type]
                return {"success": True}

            if action == "screenshot":
                img = await asyncio.to_thread(pyautogui.screenshot)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode()
                return {"image_base64": encoded}
        except Exception as exc:  # pragma: no cover – runtime errors
            raise ToolError(f"Computer action failed: {exc}") from exc

        return {"success": False}
