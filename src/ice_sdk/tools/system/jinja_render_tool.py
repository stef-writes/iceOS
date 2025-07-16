from __future__ import annotations

"""Render a Jinja2 template string with a context object.

Falls back to Python ``str.format`` when Jinja2 is unavailable so the tool
remains usable in lightweight environments.
"""

import importlib  # noqa: E402
from typing import Any, ClassVar, Dict, List  # noqa: E402

from ..base import BaseTool, ToolError  # noqa: E402

__all__ = ["JinjaRenderTool"]


class JinjaRenderTool(BaseTool):
    """Render Jinja template to string output."""

    name: ClassVar[str] = "jinja_render"
    description: ClassVar[str] = "Render a Jinja2 template with variables."
    tags: ClassVar[List[str]] = ["jinja", "template", "utility"]

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "template": {"type": "string", "description": "Jinja2 template"},
            "context": {
                "type": "object",
                "description": "Variables available to the template",
            },
        },
        "required": ["template", "context"],
    }

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "rendered": {
                "type": "string",
                "description": "Rendered template output",
            }
        },
        "required": ["rendered"],
    }

    # ------------------------------------------------------------------
    # Helpers -----------------------------------------------------------

    @staticmethod
    def _render_with_jinja(template_str: str, ctx: Dict[str, Any]) -> str:  # noqa: D401
        """Render using Jinja2 if present else fallback."""

        try:
            jinja2 = importlib.import_module("jinja2")  # type: ignore
            env = jinja2.Environment(autoescape=True)
            template = env.from_string(template_str)
            return template.render(**ctx)
        except ModuleNotFoundError:
            # Fallback: naive str.format – not full Jinja but good enough for tests
            try:
                return template_str.format(**ctx)
            except Exception as exc:  # noqa: BLE001
                raise ToolError(f"Template rendering failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        template_str = kwargs.get("template")
        context = kwargs.get("context")
        if not isinstance(template_str, str):
            raise ToolError("'template' must be a string")
        if not isinstance(context, dict):
            raise ToolError("'context' must be an object")

        rendered = self._render_with_jinja(template_str, context)
        return {"rendered": rendered}
