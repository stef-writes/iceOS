from __future__ import annotations

import importlib
from typing import Any, Dict, List, cast

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["JinjaRenderSkill"]


class JinjaRenderSkill(SkillBase):
    """Render a Jinja2 template with context."""

    name: str = "jinja_render"
    description: str = "Render a Jinja2 template with variables."
    tags: List[str] = ["jinja", "template", "utility"]

    def get_required_config(self) -> list[str]:  # noqa: D401
        return []

    @staticmethod
    def _render_with_jinja(template_str: str, ctx: Dict[str, Any]) -> str:  # noqa: D401
        try:
            jinja2 = importlib.import_module("jinja2")  # type: ignore
            env = jinja2.Environment(autoescape=True)
            template = env.from_string(template_str)
            rendered: str = template.render(**ctx)

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

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        template = cast(str, kwargs.get("template", ""))
        ctx = cast(Dict[str, Any], kwargs.get("context", {}))
        if not isinstance(template, str):
            raise SkillExecutionError("'template' must be a string")
        if not isinstance(ctx, dict):
            raise SkillExecutionError("'context' must be a dict")

        rendered = self._render_with_jinja(template, ctx)
        return {"rendered": rendered}
