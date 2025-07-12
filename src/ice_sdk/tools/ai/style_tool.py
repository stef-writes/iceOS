"""Language style adapter tool for text transformation."""

from __future__ import annotations

import re
from typing import Any, ClassVar, Dict, Literal

from ..base import BaseTool, ToolError


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
