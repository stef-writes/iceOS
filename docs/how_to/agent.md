# How-to: Wrap an API as an Agent

In this tutorial we wrap the public *DuckDuckGo Instant-Answer* API with an **AgentNode** so it can chain tool calls, parse JSON, and provide a concise reply.

---

## 1  Create the AgentConfig

```python title="agents/duck_agent.py"
from ice_sdk.models.agent_models import AgentConfig, ModelSettings
from ice_sdk.tools.web_search import WebSearchTool

DuckAgent = AgentConfig(
    name="duck_agent",
    instructions="""
You are a helpful assistant that answers factual questions using DuckDuckGo.
If you are unsure, respond with "I don't know".
""".strip(),
    model_settings=ModelSettings(provider="openai", model="gpt-3.5-turbo"),
    tools=[WebSearchTool()]
)
```

Notes:
* Tools list is **whitelist** – the LLM can only call those.
* `max_rounds` defaults to 3; increase if you expect multiple tool calls.

Place the file anywhere under `src/` so auto-discovery picks it up.

## 2  Invoke via ScriptChain

```yaml title="chains/duck_chain.yaml"
- id: ask_duck
  type: ai
  name: AskDuck
  model: gpt-3.5-turbo
  prompt: |
    {{input.question}}
  llm_config:
    provider: openai
    max_tokens: 512
  tools:
    - name: duck_agent  # exposed automatically as a tool
  input_schema:
    type: object
    properties:
      question:
        type: string
    required: [question]
```

## 3  Run the chain

```bash
ice chain run chains/duck_chain.yaml -a '{"question": "When was Apollo 11 launched?"}'
```

The agent will decide whether to call `duck_agent` (which itself may call `web_search`).  Results propagate back to the chain.

## 4  Expose via HTTP

Because the FastAPI server already exposes `/api/v1/chain/run`, the same YAML can be executed remotely:

```bash
curl -X POST http://localhost:8000/api/v1/chain/run \
  -d @chains/duck_chain.yaml \
  -H 'Content-Type: application/x-yaml'
``` 