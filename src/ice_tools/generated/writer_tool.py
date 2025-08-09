"""Writer tool – produces a short summary from notes in a given style."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import register_tool_factory


class WriterTool(ToolBase):
    """Write a short summary from notes.

    Parameters
    ----------
    max_chars : int
        Optional maximum characters for the summary.
    """

    name: str = "writer_tool"
    description: str = Field("Write a concise summary from notes")
    max_chars: int = Field(280, ge=50, description="Maximum summary length")

    async def _execute_impl(
        self, *, notes: str, style: str = "concise"
    ) -> Dict[str, Any]:  # noqa: D401
        text = notes.strip()
        if self.max_chars and len(text) > self.max_chars:
            text = text[: self.max_chars - 3] + "..."
        summary = f"[{style}] {text}"
        return {"summary": summary}


def create_writer_tool(**kwargs: Any) -> WriterTool:
    """Factory for `WriterTool`."""

    return WriterTool(**kwargs)


register_tool_factory(
    "writer_tool", "ice_tools.generated.writer_tool:create_writer_tool"
)
