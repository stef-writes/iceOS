"""Prompt rendering helpers."""

from __future__ import annotations

from typing import Any, Dict, cast

__all__ = ["render_prompt"]


async def render_prompt(template: str, context: Dict[str, Any]) -> str:
    try:
        from jinja2 import Template

        rendered: Any = Template(template).render(**context)
        return cast(str, rendered)
    except ModuleNotFoundError:
        pass
    except Exception:
        pass
    try:
        return template.format(**context)
    except Exception:
        return template
