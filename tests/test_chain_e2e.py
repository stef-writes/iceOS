import json
import os
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

# Skip the entire module if no OpenAI key (prevents failing CI when creds are absent)
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set; e2e chain tests require access to real LLMs",
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "src" / "app" / "templates"

# Manually prime singleton services because lifespan events don't run in this test transport.
if not hasattr(app.state, "tool_service"):
    try:
        from ice_sdk import ToolService
        from ice_sdk.context.manager import GraphContextManager

        app.state.tool_service = ToolService()  # type: ignore[attr-defined]
        app.state.context_manager = GraphContextManager()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover — defensive; tests will fail if these are really missing
        pass


async def _post_chain(json_payload: dict):
    """Helper to post to the /chains/execute endpoint and assert success."""
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/chains/execute", json=json_payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success"), f"Chain execution failed: {data.get('error')}"
    return data


@pytest.mark.asyncio
async def test_story_generation_chain():
    template_path = TEMPLATES_DIR / "story_chain.json"
    chain_config = json.loads(template_path.read_text())

    data = await _post_chain(chain_config)

    # Basic sanity checks on output keys
    assert "story_generator" in data["output"]
    assert "story_summarizer" in data["output"]
    assert data["output"]["story_generator"]["output"].get("story")
    assert data["output"]["story_summarizer"]["output"], "Expected summarizer output"


@pytest.mark.asyncio
async def test_character_story_chain():
    template_path = TEMPLATES_DIR / "character_story_chain.json"
    chain_config = json.loads(template_path.read_text())

    data = await _post_chain(chain_config)

    outputs = data["output"]
    assert "character_generator" in outputs
    assert "story_generator" in outputs
    assert "character_analysis" in outputs
    assert "story_summarizer" in outputs

    assert outputs["story_summarizer"]["output"].get("summary"), "Missing summary text" 