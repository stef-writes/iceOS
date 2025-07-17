"""Live LLM integration test for *Chat-in-a-Box* demo.

The test **only** executes when the environment variable ``OPENAI_API_KEY`` is
set so that CI can opt-in via secret injection.  When the key is absent the
case is *skipped* without failing the suite, keeping default runs offline.

We deliberately hit the real provider stack end-to-end (PromptBuilder +
Validator nodes) and verify that the final Deployment tool returns an
``embed_script`` value.  The deployment call itself targets a dummy endpoint
so network failures fall back to the deterministic snippet path.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ice_sdk.plugin_discovery import load_module_from_path
from ice_sdk.services import ServiceLocator

# ---------------------------------------------------------------------------
# Collection-time guard – skip when no provider key available
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    "OPENAI_API_KEY" not in os.environ,
    reason="Requires live OpenAI credentials (OPENAI_API_KEY)",
)

# ---------------------------------------------------------------------------
# Helper – lazy load the chain module
# ---------------------------------------------------------------------------

_CHAIN_PATH = (
    Path(__file__).parent.parent.parent
    / "examples"
    / "demo_portfolio"
    / "chat_in_a_box"
    / "chat_in_a_box.chain.py"
)


@pytest.mark.asyncio
async def test_chat_in_a_box_end_to_end() -> None:  # noqa: D401
    """Run the demo chain and assert the embed snippet is produced."""

    # Ensure fresh registry to avoid duplicate tool registration
    ServiceLocator.clear()
    import sys

    sys.modules.pop("chat_in_a_box_chain", None)
    mod = load_module_from_path(_CHAIN_PATH)

    chain = getattr(mod, "chain")

    # Seed initial context required by PromptBuilder -------------------------
    ctx = chain.context_manager.get_context()
    assert ctx is not None  # defensive: ScriptChain sets the context

    # Create a temporary directory for documents
    docs_dir = Path("test_docs")
    docs_dir.mkdir(exist_ok=True)

    ctx.metadata.update(
        {
            "tone": "supportive",
            "documents_dir": str(docs_dir),  # Changed from kb_url
            "guardrails": ["no disallowed content"],
        }
    )

    # Execute end-to-end ------------------------------------------------------
    result = await chain.execute()

    assert result.success is True
    assert result.output is not None
    assert "deploy" in result.output
    deploy_res = result.output["deploy"]
    assert deploy_res.success is True
    assert deploy_res.output is not None and "embed_script" in deploy_res.output
    assert deploy_res.output["embed_script"].startswith("<script")
