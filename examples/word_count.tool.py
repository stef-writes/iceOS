from __future__ import annotations

"""Example deterministic tool used in the CLI quick-start tutorial.

Add this file to your project root (or ``examples/``) then run::

    ice tool ls        # should list 'word_count'
    ice tool test word_count --args '{"text":"hello world"}'

The class follows the *BaseTool* contract: it declares ``name``,
``description``, ``parameters_schema`` and an async ``run`` method.
"""

from typing import Any, ClassVar, Dict

from ice_sdk.tools.base import BaseTool, ToolContext


class WordCountTool(BaseTool):
    """Count the number of words in the given text."""

    # Metadata -----------------------------------------------------------------
    name: ClassVar[str] = "word_count"
    description: ClassVar[str] = "Return the number of words in the given text"
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Input text to count words for",
            }
        },
        "required": ["text"],
    }

    # Business logic -----------------------------------------------------------
    async def run(self, ctx: ToolContext, *, text: str) -> Dict[str, int]:  # type: ignore[override]
        """Return a dict with the word count.

        Args:
            ctx: Execution context (unused here but required by interface).
            text: The input string to count words in.
        """
        # Simple deterministic operation – no external side-effects.
        return {"count": len(text.split())} 