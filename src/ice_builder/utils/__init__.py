"""Authoring-time utilities for Frosty and other blueprint builders.

This namespace supersedes the old *ice_sdk.utils* package.  For a smooth
transition we re-export commonly used helpers so existing callers keep working
until imports are updated.
"""

from __future__ import annotations

# Re-export selected helpers ---------------------------------------------------
from .agent_factory import AgentFactory  # type: ignore
from .coercion import auto_coerce, schema_match  # type: ignore
from .prompt_renderer import render_prompt  # type: ignore

__all__: list[str] = [
    "AgentFactory",
    "auto_coerce",
    "schema_match",
    "render_prompt",
]
