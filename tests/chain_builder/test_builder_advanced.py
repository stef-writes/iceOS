from __future__ import annotations

import ast

from ice_cli.chain_builder.engine import BuilderEngine


def test_advanced_settings_render() -> None:  # noqa: D401
    """BuilderEngine should emit retries/timeout/cache when advanced enabled."""

    draft = BuilderEngine.start(total_nodes=1, chain_name="adv_chain")

    # Persist question
    BuilderEngine.submit_answer(draft, "persist", "y")

    # Node answers ----------------------------------------------------------
    BuilderEngine.submit_answer(draft, "type", "tool")
    BuilderEngine.submit_answer(draft, "name", "adv_tool")
    BuilderEngine.submit_answer(draft, "deps", "")
    BuilderEngine.submit_answer(draft, "adv", "y")
    BuilderEngine.submit_answer(draft, "retries", "3")
    BuilderEngine.submit_answer(draft, "timeout", "60")
    BuilderEngine.submit_answer(draft, "cache", "n")

    source = BuilderEngine.render_chain(draft)

    assert "retries=3" in source
    assert "timeout=60" in source
    assert "use_cache=False" in source

    # Ensure valid Python ---------------------------------------------------
    ast.parse(source)
