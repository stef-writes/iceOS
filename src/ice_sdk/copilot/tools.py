from __future__ import annotations

import ast
import json
import logging
from typing import Any, List

from ice_sdk.tools.base import BaseTool, ToolContext

__all__ = [
    "VoiceApplierTool",
    "FormatOptimizerTool",
    "PlatformSplitterTool",
]

logger = logging.getLogger(__name__)


def _parse(raw: str) -> List[Any]:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        try:
            parsed = ast.literal_eval(cleaned)
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            logger.warning("Fallback to plain list for unparsable ideas string")
            return [raw]


# ---------------------------------------------------------------------- tools
class VoiceApplierTool(BaseTool):
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


class FormatOptimizerTool(BaseTool):
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


class PlatformSplitterTool(BaseTool):
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
