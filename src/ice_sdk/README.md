# ice_sdk – Spatial Computing Developer SDK

## Purpose
`ice_sdk` is the primary public surface for _developers_ building spatial computing experiences on iceOS.
It provides:
* Typed **Node & Tool** abstractions with spatial intelligence
* **Workflow** integration for canvas-ready execution  
* **Frosty AI** integration points for contextual assistance
* A **Provider** layer (LLM, vector, embedding) with enhanced analytics
* High-level **Agent** helpers with memory and collaboration features
* **Workflow builders** for programmatic DAG construction with spatial layout hints
* **Graph analyzers** for NetworkX-powered intelligence and optimization
* Unified **Registry** for all components

> **Spatial Computing Ready**: All SDK components are designed for both traditional execution and future canvas-based experiences.

> Rule: Nothing inside `ice_sdk.*` may import from higher layers (ice_api, ice_orchestrator)

## Quick-start: Spatial Computing Workflows
```python
from ice_sdk.builders.workflow import WorkflowBuilder
from ice_core.models import LLMConfig, ModelProvider

# Build a workflow with correct field names
builder = WorkflowBuilder("spatial_demo")

# Add tool node (uses tool_name, not tool_ref)
builder.add_tool(
    "fetch", 
    tool_name="http_request",  # Correct field name
    url="https://example.com"
)

# Add LLM nodes with rich LLMConfig
builder.add_llm(
    "analyze", 
    model="gpt-4",
    prompt="Analyze this content: {content}",  # NOT prompt_template
    llm_config=LLMConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000
    )
)

builder.add_llm(
    "summarize",
    model="gpt-3.5-turbo", 
    prompt="Summarize: {analysis}",  # Single braces for Python format
    temperature=0.5  # Node-level override
)

# Connect nodes
builder.connect("fetch", "analyze")
builder.connect("analyze", "summarize")
```

### Memory-Enabled Agent Example
```python
from ice_sdk.agents import MemoryAgent, MemoryAgentConfig
from ice_sdk.memory import UnifiedMemoryConfig
from ice_core.models.llm import LLMConfig
from ice_core.models.enums import ModelProvider

# Create a memory-enabled agent
config = MemoryAgentConfig(
    llm_config=LLMConfig(
        model="gpt-4",
        provider=ModelProvider.OPENAI
    ),
    system_prompt="You are a helpful assistant with memory.",
    tools=["web_search", "calculator"],
    memory_config=UnifiedMemoryConfig(
        enable_working=True,     # Short-term memory
        enable_episodic=True,    # Conversation history
        enable_semantic=True,    # Domain knowledge
        enable_procedural=False  # Learned procedures
    )
)

# Instantiate as a Pydantic model
agent = MyMemoryAgent(config=config)

# Agent remembers past interactions
result = await agent.execute({
    "user_id": "user123",
    "query": "What did we discuss yesterday?"
})

# Store facts for future use
await agent.remember_fact("User prefers Python over JavaScript")

# Search memories
memories = await agent.search_memory("Python", ["semantic"])
```

## Package Layout (Current State)

```
ice_sdk/
├── agents/             # Agent implementations 
│   ├── agent_node.py  # Base agent (AgentNode)
│   └── memory_agent.py # Memory-enabled agents
├── memory/            # Memory subsystem
│   ├── base.py       # Base memory interface
│   ├── working.py    # Short-term memory
│   ├── episodic.py   # Conversation history
│   ├── semantic.py   # Domain knowledge
│   ├── procedural.py # Learned procedures
│   └── unified.py    # Unified memory interface
├── builders/          # Workflow construction APIs
├── context/           # Execution context management
├── llm/               # LLM operators
│   └── operators/     # Summarizer, insights, etc.
├── providers/         # External service adapters
│   └── llm_providers/ # OpenAI, Anthropic, etc.
├── services/          # Service facades and initialization
├── tools/             # Categorized tool implementations
│   ├── core/         # CSV, JSON operations
│   ├── ai/           # LLM-powered tools
│   ├── system/       # Computer tool, sleep, etc.
│   ├── web/          # HTTP, search, webhooks
│   ├── db/           # Database tools
│   └── marketplace/  # Domain-specific tools
├── utils/             # SDK-specific utilities
├── config.py          # Runtime configuration
├── decorators.py      # Enhanced @tool decorator
├── exceptions.py      # SDK exceptions
└── unified_registry.py # Single registry for all components
```

## Layer Boundaries
* Depends _only_ on `ice_core`
* Exposes **validate()** on every Node/Tool
* External I/O lives strictly inside `tools/` or `providers/`
* All cross-layer communication via ServiceLocator
* SDK does NOT import from ice_orchestrator or ice_api

## Tool Creation

### Quick Tool with @tool Decorator
```python
from ice_sdk.decorators import tool
from ice_sdk.tools.core.base import DataTool

@tool(name="data_processor", auto_generate_tests=True)
class DataProcessor(DataTool):
    """Process data files."""
    
    async def _execute_impl(self, **kwargs):
        # Tool logic here
        return {"processed": True}
```

### AI-Powered Tool
```python
from ice_sdk.tools.ai.base import AITool

@tool(name="content_analyzer")
class ContentAnalyzer(AITool):
    """Analyze content using AI."""
    
    default_model = "gpt-4"  # Override base class default
    
    async def _execute_impl(self, **kwargs):
        content = kwargs["content"]
        llm_config = self.get_llm_config()
        # Use LLM service
        return {"analysis": "..."}
```

## Key Components

### Unified Registry
Single source of truth for all registrations:
```python
from ice_sdk.unified_registry import registry, register_node

# Register a node executor
@register_node("custom")
async def custom_executor(chain, cfg, ctx):
    ...

# Direct registry access (no wrapper modules)
registry.register_agent("my_agent", "path.to.MyAgent")
registry.register_chain("my_chain", chain_instance)
registry.register_instance(NodeType.TOOL, "my_tool", tool_instance)
```

### Service Initialization
Clean initialization without layer violations:
```python
from ice_sdk.services.initialization import initialize_services
initialize_services()  # Sets up SDK services only
```

## Development
```bash
make test   # unit + integration tests
make type   # mypy --strict
```

## License
MIT 