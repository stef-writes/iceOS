import sys
import types

import pytest

from ice_sdk.runtime.prompt_renderer import render_prompt


@pytest.mark.asyncio
async def test_render_prompt_with_jinja2():
    """Ensure Jinja2 template placeholders are rendered when the dependency is present."""
    template = "Hello {{ name }}"
    result = await render_prompt(template, {"name": "Alice"})
    assert result == "Hello Alice"


@pytest.mark.asyncio
async def test_render_prompt_str_format_fallback(monkeypatch):
    """When *jinja2* is missing or unusable the helper should fall back to *str.format*."""

    # Temporarily replace the *jinja2* module with an empty stub that lacks
    # the ``Template`` attribute so ``from jinja2 import Template`` fails.
    dummy_mod = types.ModuleType("jinja2")
    monkeypatch.setitem(sys.modules, "jinja2", dummy_mod)

    template = "Hello {name}"
    result = await render_prompt(template, {"name": "Bob"})
    assert result == "Hello Bob"
