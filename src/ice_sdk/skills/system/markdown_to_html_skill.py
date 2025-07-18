from __future__ import annotations

import html
import importlib
from typing import Any, Dict, List

from ..base import SkillBase
from ...utils.errors import SkillExecutionError

__all__ = ["MarkdownToHTMLSkill"]


class MarkdownToHTMLSkill(SkillBase):
    """Convert Markdown formatted text to HTML."""

    name: str = "markdown_to_html"
    description: str = "Convert Markdown formatted text to HTML."
    tags: List[str] = ["markdown", "conversion", "utility"]

    def get_required_config(self):  # noqa: D401
        return []

    @staticmethod
    def _convert(text: str) -> str:  # noqa: D401 – helper
        try:
            markdown_mod = importlib.import_module("markdown")
            return markdown_mod.markdown(text)  # type: ignore[attr-defined]
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

    async def _execute_impl(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        md = input_data.get("markdown")
        if not isinstance(md, str):
            raise SkillExecutionError("'markdown' parameter must be a string")

        return {"html": self._convert(md)} 