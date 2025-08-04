import asyncio
import os

import pytest

if not os.getenv("ENABLE_NL_GENERATOR"):
    pytest.skip("NL generator disabled", allow_module_level=True)

from ice_builder.nl.generation.interactive_pipeline import InteractiveBlueprintPipeline
from ice_builder.nl.memory import DraftState, InMemoryDraftStore


@pytest.mark.asyncio
async def test_resume_draft_state() -> None:
    store = InMemoryDraftStore()
    session_id = "unit-test-session"

    # Simulate first interaction (no heavy LLM calls):
    first_state = DraftState(prompt_history=["say hello"], mermaid_versions=["graph TD; A-->B"], locked_nodes=["A"])
    await store.save(session_id, first_state)

    # New pipeline should restore that state automatically
    pipe = InteractiveBlueprintPipeline("ignored prompt", session_id=session_id, store=store)
    # Trigger lazy init
    await pipe._ensure_initialized()  # type: ignore[attr-defined, protected-access]

    assert pipe.state.prompt_history == ["say hello"]
    assert pipe.state.mermaid_versions == ["graph TD; A-->B"]
    assert pipe.state.locked_nodes == ["A"]
