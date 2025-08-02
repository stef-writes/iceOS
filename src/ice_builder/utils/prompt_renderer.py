"""Prompt rendering helpers (moved from ice_sdk.runtime)."""

from __future__ import annotations

from typing import Any, Dict

__all__ = ["render_prompt"]

async def render_prompt(template: str, context: Dict[str, Any]) -> str:
    try:
        from jinja2 import Template  # type: ignore

        return Template(template).render(**context)
    except ModuleNotFoundError:
        pass
    except Exception:
        pass
    try:
        return template.format(**context)
    except Exception:
        return template
