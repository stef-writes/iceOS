import pytest

from ice_core.models.llm import MessageTemplate
from ice_core.registry.prompt_template import (
    PromptTemplateRegistry,
    global_prompt_template_registry,
    register_prompt_template,
)

pytestmark = [pytest.mark.unit]


def make_template() -> MessageTemplate:
    return MessageTemplate(
        role="user",
        content="Add {a} and {b}",
        min_model_version="gpt-4",
        provider="openai",
    )


def test_register_and_get_roundtrip() -> None:
    registry = PromptTemplateRegistry()
    tmpl = make_template()
    registry.register("adder", tmpl)

    assert len(registry) == 1
    fetched = registry.get("adder")
    assert fetched is tmpl


def test_duplicate_registration_raises() -> None:
    registry = PromptTemplateRegistry()
    tmpl = make_template()
    registry.register("dup", tmpl)
    with pytest.raises(ValueError):
        registry.register("dup", tmpl)


def test_global_singleton_available() -> None:
    name = "singleton_adder"
    tmpl = make_template()
    global_prompt_template_registry.register(name, tmpl)
    assert global_prompt_template_registry.get(name) is tmpl


def test_register_decorator() -> None:
    registry = PromptTemplateRegistry()

    @register_prompt_template("decorated")
    def _tpl() -> MessageTemplate:
        return make_template()

    assert global_prompt_template_registry.get("decorated").content.startswith("Add")


def test_missing_template_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        global_prompt_template_registry.get("does.not.exist") 