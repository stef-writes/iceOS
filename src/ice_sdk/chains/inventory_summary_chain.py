from __future__ import annotations

"""InventorySummaryChain – reusable chain that summarises CSV rows, derives insights and renders HTML."""

from typing import List, Dict, Any

from ice_core.models.node_models import LLMOperatorConfig, SkillNodeConfig, NestedChainConfig, LLMConfig
from ice_core.models.enums import ModelProvider
from ice_orchestrator.workflow import Workflow
from ice_sdk.registry.chain import global_chain_registry


class InventorySummaryChain(Workflow):
    """4-step mini-workflow reused by inventory report demos."""

    def __init__(self):
        nodes = self._build_nodes()
        super().__init__(nodes=nodes, name="inventory_summary", version="1.0.0")

    # ------------------------------------------------------------------ helper
    def _build_nodes(self) -> List[Any]:  # noqa: ANN401 – heterogeneous list
        """Return node configurations.

        Expects *rows_json* to be present in execution context (provided by a
        preceding csv_reader node in the parent workflow).
        """

        nodes: List[Any] = []

        # 1. Summarise CSV --------------------------------------------------
        nodes.append(
            LLMOperatorConfig(
                id="summarise",
                type="llm",
                name="Summarise Dataset",
                dependencies=[],  # injected at runtime via context
                model="gpt-4o",
                prompt=(
                    "You are a data assistant. Summarise the following CSV rows in under 150 tokens.\n\n{{ rows_json }}"
                ),
                llm_config=LLMConfig(provider=ModelProvider.OPENAI),
                input_schema={"rows_json": "str"},
                output_schema={"text": "str"},
            )
        )

        # 2. Generate insights ---------------------------------------------
        nodes.append(
            LLMOperatorConfig(
                id="insights",
                type="llm",
                name="Generate Insights",
                dependencies=["summarise"],
                model="gpt-4o",
                prompt=(
                    "Given this summary, produce 3-5 actionable insights as a JSON list under key 'insights'.\n\n{{ summarise.text }}"
                ),
                llm_config=LLMConfig(provider=ModelProvider.OPENAI),
                input_schema={"summary": "str"},
                output_schema={"text": "str"},
            )
        )

        # 3. Render HTML via jinja_render tool ------------------------------
        nodes.append(
            SkillNodeConfig(
                id="render_report",
                type="tool",
                name="Render HTML Report",
                dependencies=["summarise", "insights"],
                tool_name="jinja_render",
                tool_args={
                    "template": (
                        "<html><head><title>Inventory Report</title></head><body>"
                        "<h1>Dataset Summary</h1><p>{{ summary }}</p>"
                        "<h2>Insights</h2><ul>{% for i in insights %}<li>{{ i }}</li>{% endfor %}</ul>"
                        "</body></html>"
                    ),
                    "context": {"summary": "{summarise.text}", "insights": "{insights.text}"},
                },
                input_schema={"template": "str", "context": "dict"},
                output_schema={"rendered": "str"},
            )
        )

        return nodes


# Register with global registry on import ------------------------------------

global_chain_registry.register("inventory_summary", InventorySummaryChain()) 