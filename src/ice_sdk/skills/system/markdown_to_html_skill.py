from __future__ import annotations

import html
import importlib
from typing import Any, Dict, List, Optional

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["MarkdownToHTMLSkill"]


class MarkdownToHTMLSkill(SkillBase):
    """Convert Markdown formatted text to HTML."""

    name: str = "markdown_to_html"
    description: str = "Convert Markdown formatted text to HTML."
    tags: List[str] = ["markdown", "conversion", "utility"]

    def get_required_config(self) -> list[str]:  # noqa: D401
        return []

    @staticmethod
    def _convert(text: str) -> str:  # noqa: D401 – helper
        try:
            markdown_mod = importlib.import_module("markdown")  # type: ignore
            return str(markdown_mod.markdown(text))  # type: ignore[attr-defined,arg-type]
        except ModuleNotFoundError:
            lines = text.splitlines()
            out: List[str] = []
            for line in lines:
                if line.startswith("# "):
                    out.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
                elif line.startswith("## "):
                    out.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
                else:
                    out.append(f"<p>{html.escape(line.strip())}</p>")
            return "\n".join(out)

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        markdown_content: Optional[str] = kwargs.get("markdown_content") or kwargs.get(
            "markdown"
        )
        if not isinstance(markdown_content, str):
            raise SkillExecutionError("'markdown_content' must be a string")

        html_output = self._convert(markdown_content)
        return {"html": html_output}
