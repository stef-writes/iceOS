from ice_sdk.capabilities import CapabilityCard
from ice_sdk.tools.builtins.deterministic import SleepTool
from ice_sdk.tools.service import ToolService


def test_from_tool_cls():
    """CapabilityCard.from_tool_cls should map Tool metadata correctly."""

    card = CapabilityCard.from_tool_cls(SleepTool)

    assert card.id == "sleep"
    assert card.kind == "tool"
    assert card.name == "sleep"  # SleepTool defines name = "sleep"
    assert card.description  # non-empty
    assert card.parameters_schema is not None
    # SleepTool defines taxonomy tags
    assert card.tags == ["utility", "time"]


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
    assert any(
        card.id == "dummy_tool" and card.description == "Just a dummy for tests"
        for card in cards
    )


# ---------------------------------------------------------------------------
# New: purpose / examples fields -------------------------------------------
# ---------------------------------------------------------------------------


def test_card_purpose_examples_mapping():
    """CapabilityCard should capture purpose/examples when provided by Tool."""

    from ice_sdk.tools.base import BaseTool, ToolContext

    class VerboseTool(BaseTool):
        name = "verbose_tool"
        description = "Verbose tool for testing purpose field"
        purpose = "Demonstrates how purpose and examples are surfaced."
        examples = [
            {
                "input": {"text": "hello"},
                "output": {"text": "HELLO"},
            }
        ]

        async def run(self, ctx: ToolContext, *, text: str):  # type: ignore[override]
            return {"text": text.upper()}

    card = CapabilityCard.from_tool_cls(VerboseTool)

    assert card.purpose == VerboseTool.purpose
    assert card.examples == VerboseTool.examples


# ---------------------------------------------------------------------------
# AiNode → CapabilityCard ---------------------------------------------------
# ---------------------------------------------------------------------------


def test_ai_node_capability_card():
    """AiNodeConfig should map into a CapabilityCard via helper."""

    from ice_sdk.models.config import LLMConfig
    from ice_sdk.models.node_models import AiNodeConfig

    node = AiNodeConfig(
        id="summary_ai",
        name="SummarisePDF",
        model="gpt-3.5-turbo",
        prompt="Summarise {text}",
        llm_config=LLMConfig(),
        allowed_tools=["web_search"],
        output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
    )

    card = CapabilityCard.from_ai_node_cfg(node)

    assert card.id == "summary_ai"
    assert card.kind == "ai_node"
    assert card.required_tools == ["web_search"]
    assert card.output_schema is not None
