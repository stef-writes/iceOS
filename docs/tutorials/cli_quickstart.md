# iceOS CLI Quick-Start – Build Your First Workflow in 5 Minutes

> Target audience: "vibe" developers – comfortable in a terminal, new to iceOS.<br/>
> Goal: create a brand-new Tool, wire it into a ScriptChain with an LLM node, and execute with hot-reload.

---

## 0  Prerequisites

```bash
pip install -e .[test]        # or `make install` if inside the repo
export OPENAI_API_KEY=sk-…    # any provider keys the LLM node will need
```

---

## 1  Scaffold a Tool

```bash
# 1.1 Generate a new tool module
ice tool new WordCount

# A file `word_count.tool.py` now exists in the CWD.
# Open it in your editor – it looks like this (boilerplate omitted):
```

```python
class WordCountTool(BaseTool):
    name = "word_count"
    description = "Return the number of words in the given text"

    async def run(self, ctx: ToolContext, text: str) -> dict[str, int]:
        return {"count": len(text.split())}
```

> **Edit** the generated file so `run()` matches the snippet above, then save.

### 1.2 Test the Tool in isolation

```bash
ice tool test word_count --args '{"text":"hello ice world"}'
```

Expected JSON output:
```json
{"count": 3}
```

---

## 2  Create a Chain File

Make a new file `my_first_chain.py` and paste:

```python
from __future__ import annotations

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig

# 1) Tool node – calls your freshly minted WordCountTool
word_count_node = ToolNodeConfig(
    id="wc1",
    type="tool",
    tool_name="word_count",
    tool_args={"text": "iceOS makes orchestrating LLMs fun"},
)

# 2) Ai node – asks GPT to comment on the word count
ai_node = AiNodeConfig(
    id="ai1",
    type="ai",
    name="commentator",
    model="gpt-3.5-turbo",
    prompt=(
        "We just counted {{wc}} words. Is that a big sentence?"
    ),
    # pull the word-count output via input mapping
    input_mappings={
        "wc": {
            "source_node_id": "wc1",
            "source_output_key": "count",
        }
    },
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-3.5-turbo",
        temperature=0.2,
        max_tokens=100,
    ),
)

chain = ScriptChain(nodes=[word_count_node, ai_node], name="demo_chain")

# `ice run` will auto-discover if we expose either variable
# or this helper:

def get_chain() -> ScriptChain:  # optional convenience for CLI
    return chain
```

Key bits:
* **ToolNodeConfig** executes your custom tool.
* **AiNodeConfig** references that result using `input_mappings`.

---

## 3  Run the Workflow

```bash
ice run my_first_chain.py --watch
```

Output shows two node executions, token usage and the LLM's comment. With `--watch` on, any save in the editor will auto-re-run.

---

## 4  Next Steps

1. Swap `tool_args` to accept runtime input (e.g. pass text from CLI flags).  
2. Add a second AiNode that rewrites the sentence as a haiku.  
3. Deploy: `uvicorn app.main:app` and send the same chain JSON to `/api/v1/workflow`.

🎉 You just created a tool, an LLM node, and executed a multi-node ScriptChain – all from the command line. 