"""Utility helpers for prompt rendering.

Provides a single ``render_prompt`` function that can be used by executors or
custom tools to interpolate context values inside a prompt template.

The default implementation tries to use **Jinja2** – if it is available in the
runtime environment – because Jinja supports conditionals, loops and filters
that plain ``str.format`` cannot express.  When Jinja2 is missing the helper
falls back to Python's builtin ``str.format`` which still covers the majority
of simple placeholder substitutions.

Keeping the renderer in ``ice_sdk.utils`` avoids any dependency from `app.*`
which would break the repository layering contract (#4).
"""

from __future__ import annotations

from typing import Any, Dict

__all__ = ["render_prompt"]


async def render_prompt(template: str, context: Dict[str, Any]) -> str:  # noqa: D401
    """Render *template* using *context*.

    The operation is **side-effect free** and therefore lives outside tool
    implementations (repo rule #2).

    1. Attempt Jinja2 – if the package can be imported.
    2. Fallback to ``str.format``.

    Parameters
    ----------
    template:
        The raw prompt template containing ``{{ placeholder }}`` or
        ``{placeholder}`` expressions depending on the renderer.
    context:
        Key/value map made available to the template.  Nested access works with
        Jinja2 (``{{ user.name }}``) but not with ``str.format``.
    """

    # ------------------------------------------------------------------
    # 1. Try Jinja2 for full-featured templating ------------------------
    # ------------------------------------------------------------------
    try:
        from jinja2 import Template  # type: ignore

        return Template(template).render(**context)
    except ModuleNotFoundError:
        # Jinja2 not installed – fall back gracefully.
        pass
    except Exception:
        # Any other Jinja rendering error → ignore and fall back.
        pass

    # ------------------------------------------------------------------
    # 2. Plain Python ``str.format`` fallback ---------------------------
    # ------------------------------------------------------------------
    try:
        return template.format(**context)
    except Exception:
        # As a last-resort return the unmodified template to avoid crashing the
        # orchestrator.  The LLM will receive the placeholders verbatim which
        # is still usable in debugging scenarios.
        return template
