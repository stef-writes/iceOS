import os
import pytest

from ice_core.models.llm import LLMConfig, ModelProvider
from ice_sdk.providers.llm_service import LLMService

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not OPENAI_API_KEY, reason="requires OPENAI_API_KEY"),
]


@pytest.mark.asyncio
async def test_llm_service_basic_generation() -> None:
    svc = LLMService()
    cfg = LLMConfig(provider=ModelProvider.OPENAI, model="gpt-4o", max_tokens=10)
    text, usage, error = await svc.generate(llm_config=cfg, prompt="Say hello")

    assert error is None
    assert text.strip() != "" 