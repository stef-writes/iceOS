import pytest

from app.models.config import LLMConfig
from app.models.node_models import AiNodeConfig
from app.nodes.ai.llm_executor import llm_execute


class DummyLLMService:
    """LLM service that always returns an empty completion."""

    async def generate(
        self,
        llm_config,
        prompt_template,
        context=None,
        tools=None,
        timeout_seconds=30,
        max_retries=2,
    ):
        return "", {}, None  # text, usage, error


class DummyToolService:
    async def execute(self, name, args):
        return {"success": True, "output": {"dummy": True}}


class DummyContextManager:
    ...


@pytest.mark.asyncio
async def test_translator_empty_output_marks_failure():
    llm_cfg = LLMConfig(model="gpt-4", provider="openai")
    node_cfg = AiNodeConfig(
        id="translator",
        type="ai",
        model="gpt-4",
        prompt="Translate: {text}",
        llm_config=llm_cfg,
        output_schema={"text": "str"},
    )
    result = await llm_execute(
        config=node_cfg,
        context_manager=DummyContextManager(),
        llm_config=llm_cfg,
        llm_service=DummyLLMService(),
        tool_service=DummyToolService(),
        context={"text": "hola"},
    )
    assert not result.success
    assert result.error is not None 