from __future__ import annotations

import importlib
from typing import Any, Dict, List

from ..base import SkillBase
from ...utils.errors import SkillExecutionError

__all__ = ["JinjaRenderSkill"]


class JinjaRenderSkill(SkillBase):
    """Render a Jinja2 template with context."""

    name: str = "jinja_render"
    description: str = "Render a Jinja2 template with variables."
    tags: List[str] = ["jinja", "template", "utility"]

    def get_required_config(self):  # noqa: D401
        return []

    @staticmethod
    def _render_with_jinja(template_str: str, ctx: Dict[str, Any]) -> str:  # noqa: D401
        try:
            jinja2 = importlib.import_module("jinja2")  # type: ignore
            env = jinja2.Environment(autoescape=True)
            template = env.from_string(template_str)
            rendered = template.render(**ctx)

            # When developers use *format*-style placeholders ("{name}") Jinja2
            # leaves them untouched.  Detect that scenario and fall back to
            # Python's ``str.format`` so templates written for the legacy
            # *HttpRequestTool* continue to work.
            if rendered == template_str and "{" in template_str:
                return template_str.format(**ctx)

            return rendered
        except ModuleNotFoundError:
            try:
                return template_str.format(**ctx)
            except Exception as exc:  # noqa: BLE001
                raise SkillExecutionError(f"Template rendering failed: {exc}") from exc

    async def _execute_impl(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        template_str = input_data.get("template")
        context = input_data.get("context")
        if not isinstance(template_str, str):
            raise SkillExecutionError("'template' must be a string")
        if not isinstance(context, dict):
            raise SkillExecutionError("'context' must be an object")

        return {"rendered": self._render_with_jinja(template_str, context)} 