from __future__ import annotations

import ast

from ice_cli.chain_builder.engine import BuilderEngine


def _feed_answers(draft, answers):  # noqa: D401 – helper
    """Feed (key, value) pairs into :pyclass:`BuilderEngine` in order."""
    for key, value in answers:
        BuilderEngine.submit_answer(draft, key, value)


def test_builder_engine_render_valid_python() -> None:
    """BuilderEngine should render syntactically valid Python."""

    # Start a 2-node draft ----------------------------------------------------
    draft = BuilderEngine.start(total_nodes=2, chain_name="demo_chain")

    # Simulate Q&A loop -------------------------------------------------------
    # Node 0 – tool -----------------------------------------------------------
    _feed_answers(
        draft,
        [
            ("type", "tool"),
            ("name", "echo_start"),
            ("model", ""),  # no-op for tool node, required to advance state
        ],
    )

    # Node 1 – ai -------------------------------------------------------------
    _feed_answers(
        draft,
        [
            ("type", "ai"),
            ("name", "ask_llm"),
            ("model", "gpt-3.5-turbo"),
        ],
    )

    # Assertions -------------------------------------------------------------
    assert len(draft.nodes) == 2
    assert draft.nodes[0]["type"] == "tool"
    assert draft.nodes[1]["type"] == "ai"

    # Render and validate Python syntax --------------------------------------
    source = BuilderEngine.render_chain(draft)
    # ``ast.parse`` raises *SyntaxError* if the template is invalid.
    ast.parse(source)

    # Render Mermaid diagram -------------------------------------------------
    mermaid = BuilderEngine.render_mermaid(draft)
    assert mermaid.startswith("graph LR")
    # Expect 2 nodes represented
    assert "[TOOL:" in mermaid.upper()
    assert "[AI:" in mermaid.upper() 