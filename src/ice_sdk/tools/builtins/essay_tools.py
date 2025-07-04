"""Essay-specific built-in tools.

These utility tools are lightweight and *deterministic* – they perform no
network requests so they are safe for unit-testing without external
credentials.  Any heavy I/O or LLM calls should be added later inside the
`run` method while respecting project rule #2 (side-effects only inside
tool implementations).
"""

from __future__ import annotations

import re
from typing import Any, ClassVar, Dict, List, Literal

from ice_sdk.tools.base import BaseTool, ToolError

__all__: list[str] = [
    "LanguageStyleAdapterTool",
    "KeywordDensityTool",
]


# ---------------------------------------------------------------------------
#  LanguageStyleAdapterTool --------------------------------------------------
# ---------------------------------------------------------------------------
class LanguageStyleAdapterTool(BaseTool):
    """Rewrite *text* in a requested writing style.

    The current implementation is intentionally **simple & offline** so the
    test-suite can run without external LLM credentials.  For production use
    you can swap the naive transformations for a call to
    ``ice_sdk.providers.LLMService`` while keeping the same public interface.
    """

    name: ClassVar[str] = "language_style_adapter"
    description: ClassVar[str] = "Rewrite text in a specified writing style"

    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Original text"},
            "style": {
                "type": "string",
                "enum": ["academic", "casual", "persuasive"],
                "description": "Target writing style",
            },
        },
        "required": ["text", "style"],
    }

    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "styled_text": {"type": "string", "description": "Rewritten text"}
        },
        "required": ["styled_text"],
    }

    async def run(self, **kwargs: Any) -> Dict[str, str]:  # type: ignore[override]
        text: str = kwargs.get("text", "")  # type: ignore[assignment]
        style: Literal["academic", "casual", "persuasive"] | str = kwargs.get(
            "style",
            "academic",
        )

        if not text:
            raise ToolError("'text' argument is required")

        # Naïve offline style transformations – can be replaced by LLM call.
        if style == "academic":
            transformed = _to_academic(text)
        elif style == "casual":
            transformed = _to_casual(text)
        elif style == "persuasive":
            transformed = _to_persuasive(text)
        else:
            raise ToolError(f"Unsupported style: {style}")

        return {"styled_text": transformed}


# ---------------------------------------------------------------------------
#  KeywordDensityTool --------------------------------------------------------
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
#  Helpers – naive style transformations ------------------------------------
# ---------------------------------------------------------------------------


def _to_academic(text: str) -> str:  # noqa: D401 – helper
    # Expand common contractions and add a formality booster phrase.
    mapping = {
        r"\bcan't\b": "cannot",
        r"\bwon't\b": "will not",
        r"\bisn't\b": "is not",
        r"\baren't\b": "are not",
        r"\bI'm\b": "I am",
        r"\bI've\b": "I have",
        r"\bwe're\b": "we are",
    }
    result = text
    for pat, repl in mapping.items():
        result = re.sub(pat, repl, result, flags=re.IGNORECASE)
    return "Furthermore, " + result.rstrip(" .") + "."


def _to_casual(text: str) -> str:  # noqa: D401 – helper
    result = text.replace("you", "ya").replace("your", "ya'lls")
    return "Hey there! " + result


def _to_persuasive(text: str) -> str:  # noqa: D401 – helper
    return (
        "It is evident that " + text + " Therefore, one must agree with this position."
    )
