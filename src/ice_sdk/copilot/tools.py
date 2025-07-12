from __future__ import annotations

import ast
import json
import logging
from typing import Any

from ice_sdk.tools.base import BaseTool, ToolContext

__all__ = [
    "VoiceApplierTool",
    "FormatOptimizerTool",
    "PlatformSplitterTool",
]

logger = logging.getLogger(__name__)


def _parse(raw: str) -> list[Any]:
    """Parse *raw* JSON/\`repr\` string into a list.

    Guarantees a **list** return so downstream code can rely on consistent
    structure. Falls back gracefully when the input cannot be parsed.
    """
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        temp = json.loads(cleaned)
        if isinstance(temp, list):
            return temp  # type: ignore[return-value]
        return [temp]
    except Exception:
        try:
            parsed = ast.literal_eval(cleaned)
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            logger.warning("Fallback to plain list for unparsable ideas string")
            return [raw]


# ---------------------------------------------------------------------- tools
class VoiceApplierTool(BaseTool):  # type: ignore[misc]  # Pydantic BaseModel subclass dynamics
    name = "voice_applier"
    description = "Apply stylistic voice rules."
    parameters_schema = {
        "type": "object",
        "properties": {
            "ideas": {"type": "array", "items": {"type": "string"}},
            "rules_path": {"type": "string"},
        },
        "required": ["ideas"],
    }
    output_schema = {"ideas": "list"}

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:
        raw = kwargs.get("ideas", [])
        ideas = _parse(raw) if isinstance(raw, str) else raw
        if isinstance(ideas, dict) and "ideas" in ideas:
            ideas = ideas["ideas"]
        return {"ideas": ideas}


class FormatOptimizerTool(BaseTool):  # type: ignore[misc]  # dynamics
    name = "format_optimizer"
    description = "Trim whitespace & fix punctuation."
    parameters_schema = {
        "type": "object",
        "properties": {
            "ideas": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["ideas"],
    }
    output_schema = {"ideas": "list"}

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:
        raw = kwargs.get("ideas", [])
        ideas = _parse(raw) if isinstance(raw, str) else raw
        if isinstance(ideas, dict) and "ideas" in ideas:
            ideas = ideas["ideas"]
        cleaned = [s.strip() for s in ideas]
        return {"ideas": cleaned}


class PlatformSplitterTool(BaseTool):  # type: ignore[misc]  # dynamics
    name = "platform_splitter"
    description = "Create Twitter / LinkedIn variants."
    parameters_schema = {
        "type": "object",
        "properties": {
            "ideas": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["ideas"],
    }
    output_schema = {"twitter": "list", "linkedin": "list"}

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:
        raw = kwargs.get("ideas", [])
        ideas = _parse(raw) if isinstance(raw, str) else raw
        if isinstance(ideas, dict) and "ideas" in ideas:
            ideas = ideas["ideas"]
        twitter = [s[:280] for s in ideas]
        return {"twitter": twitter, "linkedin": ideas}
