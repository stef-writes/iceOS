import pytest

from ice_sdk.capabilities import CapabilityCard
from ice_sdk.tools.service import ToolService
from ice_sdk.tools.builtins.deterministic import SleepTool


def test_from_tool_cls():
    """CapabilityCard.from_tool_cls should map Tool metadata correctly."""

    card = CapabilityCard.from_tool_cls(SleepTool)

    assert card.id == "sleep"
    assert card.kind == "tool"
    assert card.name == "sleep"  # SleepTool defines name = "sleep"
    assert card.description  # non-empty
    assert card.parameters_schema is not None
    # SleepTool has no explicit tags; default []
    assert card.tags == []


def test_toolservice_cards_exposes_builtins():
    """ToolService.cards() should yield cards for all registered built-ins."""

    svc = ToolService()  # auto_register_builtins=True by default
    card_ids = {card.id for card in svc.cards()}

    expected = {"sleep", "http_request", "sum", "web_search", "file_search", "computer"}

    # We expect at least the deterministic built-ins to be present.
    assert expected.issubset(card_ids)

    # Ensure every card's id is unique
    assert len(card_ids) == len(list(svc.cards()))


def test_custom_tool_registration_card():
    """Registering a custom tool should automatically reflect in .cards()."""

    from ice_sdk.tools.base import BaseTool, ToolContext

    class DummyTool(BaseTool):
        name = "dummy_tool"
        description = "Just a dummy for tests"
        parameters_schema = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
            },
            "required": ["foo"],
        }

        async def run(self, ctx: ToolContext, *, foo: str):  # type: ignore[override]
            return {"echo": foo}

    svc = ToolService(auto_register_builtins=False)
    svc.register(DummyTool)

    cards = list(svc.cards())
    assert any(card.id == "dummy_tool" and card.description == "Just a dummy for tests" for card in cards) 