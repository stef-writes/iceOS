from __future__ import annotations

"""Basic two-node ScriptChain used by *docs/tutorials/cli_quickstart.md*.

Run it with:

    $ ice run examples/my_first_chain.py --watch

It demonstrates:
1. A deterministic *ToolNode* that invokes the custom `WordCountTool`.
2. An *AiNode* that consumes that output and asks an LLM to comment on it.

Make sure the tool module (``word_count.tool.py``) resides in the same
project so `ToolService.discover_and_register()` can find it.
"""

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig, InputMapping
import importlib.util
from pathlib import Path

# Dynamically import the WordCountTool class from the .tool.py file so we can
# pass an instance to the ScriptChain (makes it discoverable without relying
# on the ToolService disk scan).
_tool_path = Path(__file__).parent / "word_count.tool.py"
_spec = importlib.util.spec_from_file_location("word_count_tool", _tool_path)
_wordcount_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec and _spec.loader
_spec.loader.exec_module(_wordcount_mod)  # type: ignore[arg-type]
WordCountTool = _wordcount_mod.WordCountTool  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# 1. Define nodes ------------------------------------------------------------
# ---------------------------------------------------------------------------

word_count_node = ToolNodeConfig(
    id="wc1",
    type="tool",
    name="Word Counter",
    tool_name="word_count",
    tool_args={"text": "iceOS makes orchestrating LLMs fun"},
    output_schema={"count": "int"},
)

ai_node = AiNodeConfig(
    id="ai1",
    type="ai",
    name="commentator",
    dependencies=["wc1"],
    model="gpt-3.5-turbo",
    prompt="We just counted {{wc}} words. Is that a big sentence?",
    input_mappings={
        "wc": {
            "source_node_id": "wc1",
            "source_output_key": "count",
        },
    },
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-3.5-turbo",
        temperature=0.2,
        max_tokens=100,
    ),
)

# ---------------------------------------------------------------------------
# 2. Assemble chain ----------------------------------------------------------
# ---------------------------------------------------------------------------

chain = ScriptChain(nodes=[word_count_node, ai_node], name="demo_chain", tools=[WordCountTool()])


def get_chain() -> ScriptChain:  # recognised by `ice run`
    """Return the ScriptChain instance for CLI discovery."""

    return chain 