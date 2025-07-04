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


# ---------------------------------------------------------------------------
# Helper --------------------------------------------------------------------
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


def parse_json_string(raw_str: str) -> List[Any]:  # noqa: D401
    """Return Python list parsed from *raw_str*.

    Handles plain JSON, single-quoted Python reprs and markdown code fences
    such as:  ```json\n[ ... ]\n``` .  Falls back to a single-item list
    containing the original string if parsing fails.
    """

    # Strip potential markdown fences first
    cleaned = raw_str.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except Exception:
        try:
            parsed = ast.literal_eval(cleaned)
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            logger.warning("Failed to parse ideas string – returning fallback list")
            return [raw_str]


class VoiceApplierTool(BaseTool):
    """Apply stylistic voice rules to a list of idea strings.

    For demo purposes the tool just echoes the *ideas* unchanged so the demo
    chain can run without an actual rules engine.  The implementation is
    side-effect free which complies with repository rule #2.
    """

    name = "voice_applier"
    description = "Apply voice rules (tone, wording) to marketing ideas."
    parameters_schema = {
        "type": "object",
        "properties": {
            "ideas": {"type": "array", "items": {"type": "string"}},
            "rules_path": {"type": "string"},
        },
        "required": ["ideas"],
    }
    output_schema = {"ideas": "list"}

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:  # noqa: D401
        raw = kwargs.get("ideas", [])

        if isinstance(raw, str):
            ideas = parse_json_string(raw)
        else:
            ideas = raw  # already list

        # If JSON wrapped under 'ideas', extract list
        if isinstance(ideas, dict) and "ideas" in ideas:
            ideas = ideas["ideas"]

        # A real implementation would load *rules_path* and transform *ideas*.
        # The demo keeps them unchanged.
        return {"ideas": ideas}


class FormatOptimizerTool(BaseTool):
    """Optimise post length and structure keeping original ideas intact."""

    name = "format_optimizer"
    description = "Optimise content length, fix punctuation and trim whitespace."
    parameters_schema = {
        "type": "object",
        "properties": {
            "ideas": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["ideas"],
    }
    output_schema = {"ideas": "list"}

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:  # noqa: D401
        raw = kwargs.get("ideas", [])
        if isinstance(raw, str):
            from typing import Any as _Any

            parsed: _Any = parse_json_string(raw)
            if isinstance(parsed, dict) and "ideas" in parsed:
                ideas_list = parsed["ideas"]
            else:
                ideas_list = parsed if isinstance(parsed, list) else [raw]
        else:
            ideas_list = raw

        ideas: List[str] = ideas_list
        # Trivial whitespace clean-up – extend easily.
        cleaned = [idea.strip() for idea in ideas]
        return {"ideas": cleaned}


class PlatformSplitterTool(BaseTool):
    """Split long-form ideas into Twitter and LinkedIn variants."""

    name = "platform_splitter"
    description = "Split content into platform-specific formats (Twitter, LinkedIn)."
    parameters_schema = {
        "type": "object",
        "properties": {
            "ideas": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["ideas"],
    }
    output_schema = {"twitter": "list", "linkedin": "list"}

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:  # noqa: D401
        raw = kwargs.get("ideas", [])

        if isinstance(raw, str):
            from typing import Any as _Any

            parsed: _Any = parse_json_string(raw)
            if isinstance(parsed, dict) and "ideas" in parsed:
                ideas_list = parsed["ideas"]
            else:
                ideas_list = parsed if isinstance(parsed, list) else [raw]
        else:
            ideas_list = raw

        ideas: List[str] = ideas_list  # ensure list

        # For demo, Twitter versions truncate to 280 chars, LinkedIn full.
        twitter: List[str] = [idea[:280] for idea in ideas]
        linkedin: List[str] = ideas
        return {"twitter": twitter, "linkedin": linkedin}
