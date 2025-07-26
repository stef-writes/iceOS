# Configuration Architecture

## Executive Summary: Why Duplicate Names Exist

**iceOS intentionally has duplicate class names at different layers to support our canvas-based spatial computing vision.**

The architecture separates:
1. **Blueprint Definitions** (what users create in the canvas) - `ice_core.models.*Config`
2. **Runtime Execution** (how the SDK runs internally) - `ice_sdk.*Config`

This is NOT confusion or poor design - it enables:
- ✅ Progressive canvas workflow building (already implemented in MCP API)
- ✅ Clean protocol-based execution without tight coupling
- ✅ Different abstractions for different user mental models
- ✅ Incremental blueprint construction with AI suggestions

## Design Principles

1. **Separation of Concerns**: Provider configs (HOW) vs Node configs (WHAT)
2. **Richness**: Each config should have all fields needed for robust operation
3. **Symmetry**: Similar patterns across all node types
4. **Composability**: Node configs contain provider configs

## ❌ Common Mistakes → ✅ Correct Usage

### LLMOperatorConfig
- ❌ `prompt_template` → ✅ `prompt`
- ❌ `provider` → ✅ `llm_config.provider`
- ❌ `api_key` → ✅ `llm_config.api_key`

### AgentNodeConfig  
- ❌ `agent_ref` → ✅ `package`
- ❌ `agent_name` → ✅ `package`

### ToolNodeConfig
- ❌ `tool_ref` → ✅ `tool_name`
- ❌ `args` → ✅ `tool_args`

## The Pattern

### Provider Configurations (HOW to connect/execute)
These configure external services and execution parameters:

- **`LLMConfig`** (from `ice_core.models.llm`)
  - Provider settings: `api_key`, `base_url`, `timeout`
  - Model parameters: `model`, `temperature`, `max_tokens`
  - Used by: LLMOperatorConfig, AgentNodeConfig

### Node Configurations (WHAT to do)
These define workflow behavior and contain provider configs:

- **`LLMOperatorConfig`** (from `ice_core.models.node_models`)
  - Task: Generate text using an LLM
  - Contains: `llm_config: LLMConfig`
  - Node settings: `prompt`, `output_schema`

- **`AgentNodeConfig`** (from `ice_core.models.node_models`)
  - Task: Multi-step reasoning with tools
  - Contains: `llm_config: Optional[LLMConfig]`
  - Node settings: `tools`, `memory`, `max_iterations`

- **`ToolNodeConfig`** (from `ice_core.models.node_models`)
  - Task: Execute a specific tool
  - Node settings: `tool_name`, `tool_args`
  - No provider config needed (tools are local)

## When to Use Which Configuration

### Building a Canvas Workflow?
```python
# Use ice_core configs - these serialize to blueprints
from ice_core.models import LLMOperatorConfig, AgentNodeConfig, LLMConfig

node = LLMOperatorConfig(
    id="analyzer",
    type="llm",
    model="gpt-4",
    prompt="Analyze: {data}",  # ✅ Correct field name
    llm_config=LLMConfig(      # ✅ Required field
        provider=ModelProvider.OPENAI,
        model="gpt-4",
        api_key="sk-...",
        temperature=0.8,
        max_tokens=2000
    ),
    temperature=0.7  # Node-level override
)
```

### Writing an SDK Operator?
```python
# Use SDK configs - these are for internal implementation
from ice_sdk.llm.operators.base import LLMOperatorConfig

class MyOperator(LLMOperator):
    def __init__(self):
        config = LLMOperatorConfig(  # Simple, flat config
            provider=ModelProvider.OPENAI,
            model="gpt-4",
            temperature=0.7
        )
        super().__init__(config=config)
```

### Working with MCP API?
```python
# Always use ice_core - MCP speaks blueprints
from ice_core.models import NodeConfig, LLMOperatorConfig

# This is what the canvas sends to the backend
blueprint = {
    "nodes": [
        LLMOperatorConfig(id="n1", type="llm", ...)
    ]
}
```

## Example: Rich Agent Configuration

```python
agent_node = AgentNodeConfig(
    id="researcher",
    type="agent",
    package="ice_sdk.agents.research.ResearchAgent",  # ✅ Not 'agent_ref'
    
    # Rich agent-specific settings
    tools=[
        ToolConfig(name="web_search", max_retries=3),
        ToolConfig(name="summarizer", timeout=30)
    ],
    memory={"type": "conversation", "max_turns": 10},
    max_iterations=5,  # ✅ Required field
    
    # Rich LLM configuration
    llm_config=LLMConfig(
        provider="anthropic",
        model="claude-3-opus",
        temperature=0.7,
        max_tokens=4000,
        api_key="sk-...",
        timeout=60
    )
)
```

## Quick Debugging Guide

Before writing any test:

1. **Check the actual model**:
   ```bash
   grep -n "class LLMOperatorConfig" src/ice_core/models/*.py
   ```

2. **Look at field definitions**:
   ```bash
   grep -A 20 "class LLMOperatorConfig" src/ice_core/models/node_models.py
   ```

3. **Find working examples**:
   ```bash
   grep -r "LLMOperatorConfig(" src/ --include="*.py" | head -5
   ```

## Key Rule: Import Paths Matter!

```python
# Building a workflow? Use ice_core
from ice_core.models import LLMOperatorConfig  # ✅

# Writing an SDK operator? Use ice_sdk
from ice_sdk.llm.operators.base import LLMOperatorConfig  # ✅

# NEVER mix them in the same file!
```

## Benefits of This Design

1. **Flexibility**: Each node can override provider settings
2. **Defaults**: Nodes can use system defaults when config is None
3. **Testing**: Easy to mock provider configs
4. **Evolution**: Can add new fields without breaking existing code
5. **Canvas Support**: Blueprint configs can be progressively built and validated
6. **Tool Creation**: Enhanced @tool decorator simplifies development
7. **Cost Awareness**: AI tools vs Core tools have clear boundaries 