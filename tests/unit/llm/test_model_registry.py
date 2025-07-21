import pytest
from ice_core.models.llm import LLMConfig
from ice_core.models.model_registry import is_allowed_model, list_models


def test_registry_contains_expected_models() -> None:
    ids = [m.id for m in list_models()]
    assert "gpt-4o" in ids
    assert "gpt-3.5-turbo" not in ids


def test_is_allowed_model() -> None:
    assert is_allowed_model("gpt-4o") is True
    assert is_allowed_model("gpt-3.5-turbo") is False


def test_llmconfig_rejects_banned_models() -> None:
    with pytest.raises(ValueError):
        _ = LLMConfig(model="gpt-3.5-turbo", provider="openai")  # type: ignore[arg-type]

    cfg = LLMConfig(model="gpt-4o", provider="openai")  # type: ignore[arg-type]
    assert cfg.model == "gpt-4o"
