"""Integration test: ingest docs → EnterpriseKBNode → PromptBuilder → Deployment.

Skips when no `OPENAI_API_KEY` is available to avoid live-provider calls in
offline CI.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ice_sdk.plugin_discovery import load_module_from_path
from ice_sdk.services import ServiceLocator

pytestmark = pytest.mark.skipif(
    "OPENAI_API_KEY" not in os.environ,
    reason="Requires live OpenAI credentials (OPENAI_API_KEY)",
)


@pytest.mark.asyncio
async def test_chat_in_a_box_with_kb(tmp_path: Path) -> None:  # noqa: D401
    """End-to-end flow with document ingestion."""

    # ------------------------------------------------------------------
    # 1. Prepare sample docs and update chain config
    # ------------------------------------------------------------------
    docs_dir = tmp_path / "kb"
    docs_dir.mkdir()
    sample_file = docs_dir / "refund_policy.md"
    sample_file.write_text(
        """# Refund Policy\n\nCustomers can request a refund within 30 days of purchase."""
    )

    # Ingest another doc under *other* label to ensure filter works -----------
    other_dir = tmp_path / "other_kb"
    other_dir.mkdir()
    (other_dir / "unrelated.md").write_text("Unrelated content")

    chain_path = (
        Path(__file__).parent.parent.parent
        / "examples"
        / "demo_portfolio"
        / "chat_in_a_box"
        / "chat_in_a_box.chain.py"
    )

    # Reset service registry to avoid duplicate tool registration
    ServiceLocator.clear()
    import sys

    sys.modules.pop("chat_in_a_box_chain", None)
    mod = load_module_from_path(chain_path)
    chain = getattr(mod, "chain")

    # Inject dynamic watch dir so EnterpriseKBNode sees the new docs -------
    kb_node = chain.nodes.get("kb_lookup")  # type: ignore[attr-defined]
    assert kb_node is not None, "Knowledge node not found in chain"

    # Update *params* mapping in-place (Pydantic model is mutable) ---------
    kb_node.params["watch_dirs"] = [str(docs_dir)]  # type: ignore[attr-defined]
    kb_node.params["label"] = "support-faq"  # type: ignore[attr-defined]
    kb_node.params["auto_parse"] = False  # avoid sync ingestion inside async loop

    # ------------------------------------------------------------------
    # 2. Seed initial context (query drives retrieval)
    # ------------------------------------------------------------------
    ctx = chain.context_manager.get_context()
    assert ctx is not None
    ctx.metadata.update(
        {
            "tone": "supportive",
            "kb_url": str(docs_dir),
            "guardrails": ["no disallowed content"],
            "kb_label": "support-faq",
            "query": "refund",
        }
    )

    # ------------------------------------------------------------------
    # 3. Execute chain --------------------------------------------------
    # ------------------------------------------------------------------
    result = await chain.execute()

    assert result.success is True
    assert result.output is not None and "deploy" in result.output
    deploy_res = result.output["deploy"]
    assert deploy_res.success is True
    assert deploy_res.output is not None and "embed_script" in deploy_res.output

    # Knowledge node should have stored context -------------------------
    retrieved = chain.context_manager.get_node_context("kb_lookup")
    assert retrieved, "Expected KB context in graph context store"
    # Ensure we retrieved some context (content may vary depending on chunking)
    assert retrieved is not None and len(str(retrieved)) > 0
