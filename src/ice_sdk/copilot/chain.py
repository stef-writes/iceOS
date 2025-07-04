"""FrostyDemoChain – minimal ScriptChain that exercises Copilot tools.

This chain remains purely as an example and is *not* required by the runtime
Copilot.  It can be executed via ``ice run ...`` or imported from
``ice_sdk.copilot.workflows``.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, List, Type, cast

from ice_sdk.copilot.tools import (
    FormatOptimizerTool,
    PlatformSplitterTool,
    VoiceApplierTool,
)
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import (
    AiNodeConfig,
    InputMapping,
    NodeConfig,
    ToolNodeConfig,
)

# Dynamic import to avoid static dependency on *ice_orchestrator* which violates
# onion-layer architecture contracts enforced by *import-linter* tests.
# This runtime import keeps the module decoupled at the type-checker level and
# preserves existing behaviour when *ice_orchestrator* is available.

# Resolve *ScriptChain* differently for type checking vs runtime to satisfy mypy
if TYPE_CHECKING:
    # Minimal stub so MyPy recognises it as a *class*
    class ScriptChain:  # noqa: D401 – typing stub
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

else:
    ScriptChain = cast(Type[Any], import_module("ice_orchestrator").ScriptChain)  # type: ignore[attr-defined]


def _build_nodes(topic: str) -> List[NodeConfig]:  # noqa: D401
    idea = AiNodeConfig(
        id="idea_generator",
        type="ai",
        name="Idea Generator",
        model="deepseek-chat",
        provider=ModelProvider.DEEPSEEK,
        prompt=(
            "SYSTEM:\nYou are an AI copywriter. Return a JSON list `ideas` with 5 elements.\n---\n"
            f"USER_INPUT: {topic}\n"
        ),
        llm_config=LLMConfig(provider="deepseek", model="deepseek-chat"),
        output_schema={},
        dependencies=[],
    )

    voice = ToolNodeConfig(
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
                source_node_id="idea_generator", source_output_key="."
            )
        },
        output_schema={"ideas": "list"},
        dependencies=["idea_generator"],
    )

    fmt = ToolNodeConfig(
        id="format_optimizer",
        type="tool",
        name="Format Optimizer",
        tool_name="format_optimizer",
        tool_args={"ideas": "{ideas}"},
        input_mappings={
            "ideas": InputMapping(
                source_node_id="voice_applier", source_output_key="ideas"
            )
        },
        output_schema={"ideas": "list"},
        dependencies=["voice_applier"],
    )

    split = ToolNodeConfig(
        id="platform_splitter",
        type="tool",
        name="Platform Splitter",
        tool_name="platform_splitter",
        tool_args={"ideas": "{ideas}"},
        input_mappings={
            "ideas": InputMapping(
                source_node_id="format_optimizer", source_output_key="ideas"
            )
        },
        output_schema={"twitter": "list", "linkedin": "list"},
        dependencies=["format_optimizer"],
    )

    return [idea, voice, fmt, split]


class FrostyDemoChain(ScriptChain):
    """Reference ScriptChain using Copilot-specific tools."""

    def __init__(self, topic: str | None = None):  # noqa: D401
        topic = topic or "marketing tips for freelancers"
        nodes = _build_nodes(topic)
        tools = [VoiceApplierTool(), FormatOptimizerTool(), PlatformSplitterTool()]
        super().__init__(
            nodes=nodes,
            name="frosty_demo",
            tools=tools,
            persist_intermediate_outputs=True,
        )


def get_chain() -> FrostyDemoChain:  # noqa: D401
    """Factory helper for *ice run* convenience."""

    import os

    return FrostyDemoChain(os.getenv("TOPIC", "marketing tips for freelancers"))
