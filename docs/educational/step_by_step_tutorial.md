# Step-by-Step Tutorial

Welcome! This guide walks you through building a tiny **iceOS** application from scratch while teaching the core concepts.

---
## 0. Prerequisites
* Python 3.9+  
* An OpenAI API key (`OPENAI_API_KEY`) – free tier is fine.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
```

## 1. Your first Tool
Create `my_tools/hello.py`:
```python
from pydantic import BaseModel, Field
from ice_sdk.base_tool import BaseTool

class _Params(BaseModel):
    name: str = Field(..., description="Who to greet")

class HelloTool(BaseTool):
    name = "hello"
    description = "Return a personalised greeting."
    parameters_schema = _Params

    async def run(self, *, name: str):
        return {"greeting": f"Hello, {name}!"}
```
Add to `PYTHONPATH` or package entry-points so `ToolService` discovers it.

## 2. Wrap it in an Agent
```python
from app.nodes.tool_node import ToolNodeConfig
from app.agents import NodeAgentAdapter, AgentRegistry
from app.utils.context import SessionState, GraphContextManager
from datetime import datetime

cfg = ToolNodeConfig(
    id="hello_node",
    type="tool",
    tool_name="hello",
    tool_args={},
    metadata=None,
)
node   = node_factory(cfg, context_manager=GraphContextManager())
agent  = NodeAgentAdapter(node, name="greeter")
reg    = AgentRegistry(); reg.register(agent)

session = SessionState("demo")
result  = await reg.get("greeter").execute(session, {"name": "Ada"})
print(result.output)  # => {'greeting': 'Hello, Ada!'}
```

## 3. Add an LLM Agent
```python
from app.models.node_models import AiNodeConfig, NodeMetadata
from app.models.config import LLMConfig, ModelProvider

ai_cfg = AiNodeConfig(
    id="qa_node",
    type="ai",
    model="gpt-3.5-turbo",
    prompt="Answer the question as briefly as possible: {question}",
    llm_config=LLMConfig(provider=ModelProvider.OPENAI, model="gpt-3.5-turbo"),
    metadata=NodeMetadata(node_id="qa_node", node_type="ai"),
)
qa_agent = NodeAgentAdapter(node_factory(ai_cfg, context_manager=GraphContextManager(), llm_config=ai_cfg.llm_config), name="qa")
reg.register(qa_agent)
```

## 4. Use RouterAgent
```python
from app.agents import RouterAgent
router = RouterAgent(reg)
answer = await router.execute(session, {"text": "What is the capital of France?"})
print(answer.output)
```
Router will pick `qa` because its description includes "question/answer".

## 5. Going further
* Convert a LevelBasedScriptChain into a WorkflowAgentAdapter to group multiple nodes.  
* Call an agent *inside* an AiNode using `AgentTool`.

Happy building! 