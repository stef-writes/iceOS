from __future__ import annotations

"""Markdown → HTML conversion tool.

Converts a Markdown-formatted *string* to HTML.  Uses the ``markdown`` PyPI
package when installed; otherwise falls back to a *very* lightweight (and
limited) converter that handles paragraphs and ATX headers (``#`` / ``##``).

External side-effects live only inside the ``run`` method as per repo rule #2.
"""

import html  # noqa: E402
import importlib  # noqa: E402
from typing import Any, ClassVar, Dict, List  # noqa: E402

from ..base import BaseTool, ToolError  # noqa: E402

__all__ = ["MarkdownToHTMLTool"]


class MarkdownToHTMLTool(BaseTool):
    """Convert Markdown text to HTML."""

    name: ClassVar[str] = "markdown_to_html"
    description: ClassVar[str] = "Convert Markdown formatted text to HTML."
    tags: ClassVar[List[str]] = ["markdown", "conversion", "utility"]

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "markdown": {
                "type": "string",
                "description": "Markdown content to convert",
            }
        },
        "required": ["markdown"],
    }

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "html": {
                "type": "string",
                "description": "Converted HTML content",
            }
        },
        "required": ["html"],
    }

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------

    @staticmethod
    def _convert(text: str) -> str:  # noqa: D401 – helper name
        """Return HTML for *text* using best-available converter."""

        try:
            markdown_mod = importlib.import_module("markdown")
            return markdown_mod.markdown(text)  # type: ignore[attr-defined]
        except ModuleNotFoundError:
            # Fallback: naive line-by-line conversion --------------------
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

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        markdown_text = kwargs.get("markdown")
        if not isinstance(markdown_text, str):
            raise ToolError("'markdown' parameter must be a string")

        html_out = self._convert(markdown_text)
        return {"html": html_out}
