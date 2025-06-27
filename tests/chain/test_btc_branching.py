from __future__ import annotations

from typing import Any, List

import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import (
    AiNodeConfig,
    ConditionNodeConfig,
    InputMapping,
    ToolNodeConfig,
    NodeExecutionResult,
)
from ice_sdk.providers.llm_service import LLMService
from ice_sdk.tools.base import BaseTool, ToolContext, function_tool

# ---------------------------------------------------------------------------
# Helper – deterministic LLM stub -------------------------------------------
# ---------------------------------------------------------------------------


async def _dummy_generate(
    self: LLMService,  # noqa: D401 – monkey-patch retains *self*
    llm_config: LLMConfig,  # noqa: D401
    prompt: str,  # noqa: D401
    context: dict[str, Any] | None = None,  # noqa: D401
    tools=None,  # noqa: ANN001, D401
    **_kwargs: Any,  # noqa: D401, ANN003
):
    """Return a constant tuple so no external API call is made."""
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return "OK", usage, None


# ---------------------------------------------------------------------------
# Helper – factory for the mocked CoinMarketCap tool -------------------------
# ---------------------------------------------------------------------------


def _price_tool(change_24h: float) -> BaseTool:
    """Return a new *coinmarketcap* tool instance with hard-coded data."""

    @function_tool(name_override="coinmarketcap")
    async def _tool(ctx: ToolContext, currency: str = "USD") -> dict[str, float]:  # type: ignore[override]
        return {"price": 50_000.0, "change_24h": change_24h}

    return _tool  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Shared node configuration helpers -----------------------------------------
# ---------------------------------------------------------------------------


def _build_nodes() -> List[ToolNodeConfig | AiNodeConfig | ConditionNodeConfig]:
    """Create the static part of the node graph (parameterised later)."""
    # The *get_price* node is parameterised at runtime via the injected tool.
    price_node = ToolNodeConfig(
        id="get_price",
        name="Get BTC Price",
        tool_name="coinmarketcap",
        output_schema={"price": "float", "change_24h": "float"},
    )

    route_node = ConditionNodeConfig(
        id="route",
        name="Volatility Router",
        expression="change_24h > 5 or change_24h < -5",
        true_branch=["generate_rich_content"],
        false_branch=["generate_simple_tweet"],
        dependencies=["get_price"],
        input_mappings={
            "change_24h": InputMapping(
                source_node_id="get_price", source_output_key="change_24h"
            )
        },
    )

    # Minimal LLM config – actual call is stubbed by *_dummy_generate*.
    llm_cfg = LLMConfig(provider=ModelProvider.OPENAI, model="gpt-4o")

    rich_node = AiNodeConfig(
        id="generate_rich_content",
        name="Rich Content",
        model="gpt-4o",
        prompt="Write 3 tweets and a blog post.",
        llm_config=llm_cfg,
        dependencies=["route"],
    )

    simple_node = AiNodeConfig(
        id="generate_simple_tweet",
        name="Simple Tweet",
        model="gpt-4o",
        prompt="Write one calm tweet.",
        llm_config=llm_cfg,
        dependencies=["route"],
    )

    return [price_node, route_node, rich_node, simple_node]


# ---------------------------------------------------------------------------
# Parametrised tests ---------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("change,expected_branch", [(6.3, "generate_rich_content"), (3.1, "generate_simple_tweet")])
async def test_volatility_branching(monkeypatch, change: float, expected_branch: str):
    """The *route* node should enable the correct branch based on *change_24h*."""

    # 1. Patch LLMService to avoid network traffic ----------------------
    monkeypatch.setattr(LLMService, "generate", _dummy_generate, raising=False)

    # 2. Create mocked tool matching the current scenario --------------
    price_tool = _price_tool(change)

    # 3. Assemble ScriptChain ------------------------------------------
    chain = ScriptChain(
        nodes=_build_nodes(),
        tools=[price_tool],
        name="btc_analysis_test_chain",
        persist_intermediate_outputs=False,
        use_cache=False,
    )

    # 4. Execute --------------------------------------------------------
    result = await chain.execute()

    assert result.success is True, result.error or "Chain execution failed"
    assert isinstance(result.output, dict)

    # Helper mapping convenience ---------------------------------------
    node_results: dict[str, NodeExecutionResult] = {
        k: v for k, v in result.output.items() if isinstance(v, NodeExecutionResult)
    }

    # The chosen branch should be present ------------------------------
    assert expected_branch in node_results and node_results[expected_branch].success is True

    # The *other* branch must be absent
    other_branch = (
        "generate_simple_tweet" if expected_branch == "generate_rich_content" else "generate_rich_content"
    )
    assert other_branch not in node_results

    # Route evaluation result correctness ------------------------------
    route_output = node_results["route"].output  # type: ignore[index]
    assert isinstance(route_output, dict) and "result" in route_output
    predicted = abs(change) > 5
    assert route_output["result"] is predicted 