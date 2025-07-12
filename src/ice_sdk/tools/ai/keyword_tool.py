"""Keyword density analysis tool."""

from __future__ import annotations

import re
from typing import Any, ClassVar, Dict, List

from ..base import BaseTool, ToolError


class KeywordDensityTool(BaseTool):
    """Calculate keyword density for supplied *text*.

    Returns the relative frequency (0-1) for each keyword and the total word
    count.  A simple HTML string with <mark> tags is also returned so callers
    can preview highlighted terms.
    """

    name: ClassVar[str] = "keyword_analyzer"
    description: ClassVar[str] = "Compute keyword density and highlight terms"

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Input text"},
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keywords to analyse",
            },
            "case_sensitive": {
                "type": "boolean",
                "default": False,
                "description": "Whether keyword matching is case-sensitive",
            },
        },
        "required": ["text", "keywords"],
    }

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "density": {
                "type": "object",
                "additionalProperties": {"type": "number"},
            },
            "total_words": {"type": "integer"},
            "highlighted_html": {"type": "string"},
        },
        "required": ["density", "total_words", "highlighted_html"],
    }

    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        text: str = kwargs.get("text", "")  # type: ignore[assignment]
        keywords: List[str] = kwargs.get("keywords", [])  # type: ignore[assignment]
        case_sensitive: bool = kwargs.get("case_sensitive", False)

        if not text:
            raise ToolError("'text' argument is required")
        if not keywords or not isinstance(keywords, list):
            raise ToolError("'keywords' must be a non-empty list")

        flags = 0 if case_sensitive else re.IGNORECASE

        # Tokenise on whitespace / punctuation – simple heuristic acceptable for demo.
        words = re.findall(r"[A-Za-z']+", text)
        total_words = len(words)

        density: Dict[str, float] = {}
        highlighted = text

        for kw in keywords:
            pattern = re.compile(re.escape(kw), flags)
            matches = pattern.findall(text)
            density[kw] = len(matches) / total_words if total_words else 0
            # Highlight occurrences in HTML output (case-preserving replacement).
            highlighted = pattern.sub(
                lambda m: f"<mark>{m.group(0)}</mark>", highlighted
            )

        return {
            "density": density,
            "total_words": total_words,
            "highlighted_html": highlighted,
        }
