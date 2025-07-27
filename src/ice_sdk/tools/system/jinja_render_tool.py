from __future__ import annotations

import importlib
from typing import Any, Dict, List, cast

from ...utils.errors import ToolExecutionError
from ..base import ToolBase

__all__ = ["JinjaRenderTool"]

class JinjaRenderTool(ToolBase):
    """Render a Jinja2 template with context."""

    name: str = "jinja_render"
    description: str = "Render a Jinja2 template with variables."
    tags: List[str] = ["jinja", "template", "utility"]

    def get_required_config(self) -> list[str]:
        return []

    @staticmethod
    def _render_with_jinja(template_str: str, ctx: Dict[str, Any]) -> str:
        try:
            jinja2 = importlib.import_module("jinja2")  # type: ignore
            env = jinja2.Environment(autoescape=True)
            template = env.from_string(template_str)
            rendered: str = template.render(**ctx)
            return rendered
        except ModuleNotFoundError as exc:
            raise ToolExecutionError("jinja_render", "Jinja2 module not found. Please install jinja2.") from exc
        except Exception as exc:
            raise ToolExecutionError("jinja_render", f"Template rendering failed: {exc}") from exc

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        template = cast(str, kwargs.get("template", ""))
        ctx = cast(Dict[str, Any], kwargs.get("context", {}))
        if not isinstance(template, str):
            raise ToolExecutionError("jinja_render", "'template' must be a string")
        if not isinstance(ctx, dict):
            raise ToolExecutionError("jinja_render", "'context' must be a dict")

        rendered = self._render_with_jinja(template, ctx)
        return {"rendered": rendered}
