# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path as _Path
from typing import List

# ---------------------------------------------------------------------------
# Import setup --------------------------------------------------------------
# ---------------------------------------------------------------------------


# Ensure the repository root is on ``sys.path`` so the absolute package import
# below works even when this file is executed via ``ice run`` which loads the
# module directly from its path (hence without a package context).
_PROJECT_ROOT = str(_Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from cli_demo.brand_demo.frosty_tools import (
    FormatOptimizerTool,
    PlatformSplitterTool,
    VoiceApplierTool,
)
from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import (
    AiNodeConfig,
    InputMapping,
    NodeConfig,
    ToolNodeConfig,
)

# ---------------------------------------------------------------------------
# Node definitions (minimal subset of full Frosty demo) ---------------------
# ---------------------------------------------------------------------------


def _build_nodes(topic: str) -> List[NodeConfig]:  # noqa: D401
    """Return NodeConfig list for the Frosty demo."""

    # 1. Idea generator --------------------------------------------------
    idea_node = AiNodeConfig(
        id="idea_generator",
        type="ai",
        name="Idea Generator",
        model="deepseek-chat",
        provider=ModelProvider.DEEPSEEK,
        prompt=(
            "SYSTEM:\nYou are an AI copywriter for a 26-year-old marketing freelancer.\n"
            "Return a JSON list called ideas containing exactly 5 content ideas.\n---\n"
            f"USER_INPUT: {topic}\n"
        ),
        llm_config=LLMConfig(provider="deepseek", model="deepseek-chat"),
        output_schema={},
        dependencies=[],
    )

    # 2. Voice Applier ----------------------------------------------------
    voice_node = ToolNodeConfig(
        id="voice_applier",
        type="tool",
        name="Voice Applier",
        tool_name="voice_applier",
        tool_args={
            "ideas": "{ideas}",
            "rules_path": "./knowledge_base/voice_rules.json",
        },
        input_mappings={
            "ideas": InputMapping(
                source_node_id="idea_generator",
                source_output_key=".",
            )
        },
        output_schema={"ideas": "list"},
        dependencies=["idea_generator"],
    )

    # 3. Format Optimizer --------------------------------------------------
    format_node = ToolNodeConfig(
        id="format_optimizer",
        type="tool",
        name="Format Optimizer",
        tool_name="format_optimizer",
        tool_args={"ideas": "{ideas}"},
        input_mappings={
            "ideas": InputMapping(
                source_node_id="voice_applier",
                source_output_key="ideas",
            )
        },
        output_schema={"ideas": "list"},
        dependencies=["voice_applier"],
    )

    # 4. Platform Splitter -------------------------------------------------
    split_node = ToolNodeConfig(
        id="platform_splitter",
        type="tool",
        name="Platform Splitter",
        tool_name="platform_splitter",
        tool_args={"ideas": "{ideas}"},
        input_mappings={
            "ideas": InputMapping(
                source_node_id="format_optimizer",
                source_output_key="ideas",
            )
        },
        output_schema={"twitter": "list", "linkedin": "list"},
        dependencies=["format_optimizer"],
    )

    return [idea_node, voice_node, format_node, split_node]


# ---------------------------------------------------------------------------
# Demo chain wrapper --------------------------------------------------------
# ---------------------------------------------------------------------------


class FrostyDemoChain(ScriptChain):
    """ScriptChain for the "Frosty personal brand" demo (reduced flow)."""

    def __init__(self, topic: str | None = None):
        topic = topic or "marketing tips for freelancers"
        nodes: List[NodeConfig] = _build_nodes(topic)
        # Register stub tool instances ----------------------------------
        tools = [VoiceApplierTool(), FormatOptimizerTool(), PlatformSplitterTool()]
        super().__init__(
            nodes=nodes,
            name="frosty_demo",
            tools=tools,
            persist_intermediate_outputs=True,
        )


# Factory helper used by *ice run* -----------------------------------------


def get_chain() -> FrostyDemoChain:  # noqa: D401 – simple factory
    """Return a ready-to-run *FrostyDemoChain* instance.

    The topic can be customised via the *TOPIC* environment variable.
    """

    import os

    return FrostyDemoChain(topic=os.getenv("TOPIC", "marketing tips for freelancers"))
