"""Prompt rendering helpers.

Single, production-grade rendering path using Jinja2 with StrictUndefined.
No Python ``str.format`` fallback – this avoids brace-collapsing of
``{{ ... }}`` into literal ``{ ... }``.

Example:
    >>> await render_prompt("Hello {{ name }}", {"name": "world"})
    'Hello world'
"""

from __future__ import annotations

from typing import Any, Dict, cast

__all__ = ["render_prompt"]


async def render_prompt(template: str, context: Dict[str, Any]) -> str:
    """Render a template with Jinja2 only.

    Parameters
    ----------
    template : str
        Jinja2 template string with ``{{ ... }}`` placeholders.
    context : Dict[str, Any]
        Mapping of variables available to the template.

    Returns
    -------
    str
        Rendered string. On failure, returns the original template unchanged.
    """
    try:
        import jinja2

        env = jinja2.Environment(autoescape=False, undefined=jinja2.StrictUndefined)
        jinja_template = env.from_string(template)
        rendered: Any = jinja_template.render(**context)
        return cast(str, rendered)
    except Exception:
        # Fail closed: never attempt Python .format() which collapses braces
        return template
