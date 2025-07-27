# ice_sdk – Developer SDK

## Purpose
`ice_sdk` is the developer-facing SDK for building tools and workflows on iceOS. It provides:

* **Tool Development**: Base classes, decorators, and utilities for creating tools
* **Workflow Builders**: Fluent APIs for programmatic workflow construction
* **Service Locator**: Cross-layer dependency injection pattern
* **Development Utilities**: Type coercion, error handling, and developer conveniences

> **Layer Boundaries**: SDK depends only on `ice_core`. It does NOT import from `ice_orchestrator` or `ice_api`. Cross-layer dependencies use ServiceLocator.

## Quick Start: Building Tools

### Using the @tool Decorator
```python
from ice_sdk.decorators import tool
from ice_sdk.tools.base import ToolBase
from typing import Dict, Any

@tool(name="data_processor", category="core")
class DataProcessor(ToolBase):
    """Process data files with validation."""
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        file_path = kwargs["file_path"]
        # Process the file
        return {"processed": True, "rows": 100}
```

### AI-Powered Tools
```python
from ice_sdk.tools.ai.base import AITool
from ice_sdk.services import ServiceLocator

@tool(name="content_analyzer")
class ContentAnalyzer(AITool):
    """Analyze content using LLM via ServiceLocator."""
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        content = kwargs["content"]
        
        # Get LLM service via ServiceLocator (not direct import)
        llm_service = ServiceLocator.get("llm_service")
        
        result = await llm_service.generate(
            self.get_llm_config(),
            f"Analyze this content: {content}"
        )
        
        return {"analysis": result.text}
```

## Building Workflows

```python
from ice_sdk.builders.workflow import WorkflowBuilder
from ice_sdk.builders.agent import AgentBuilder, create_agent

# Build a workflow
builder = WorkflowBuilder("my_workflow")

# Add tool nodes
builder.add_tool(
    "fetch", 
    tool_name="http_request",
    url="https://api.example.com/data"
)

# Create agent configuration
agent_config = create_agent(
    name="analyzer",
    model="gpt-4",
    tools=["web_search", "calculator"],
    system_prompt="You are a data analyst"
)

# Add agent to workflow
builder.add_agent("analyze", agent_config)

# Connect nodes
builder.connect("fetch", "analyze")

# Get workflow config
workflow_config = builder.build()
```

## Package Layout

```
ice_sdk/
├── tools/              # Tool implementations
│   ├── base.py        # Base tool classes
│   ├── core/          # CSV, JSON operations
│   ├── ai/            # AI-powered tools (insights, summarizer)
│   ├── system/        # System tools (sleep, jinja)
│   ├── web/           # HTTP, search, webhooks
│   ├── db/            # Database tools
│   └── marketplace/   # Domain-specific tools
├── builders/          # Workflow and agent builders
│   ├── workflow.py    # WorkflowBuilder
│   └── agent.py       # AgentBuilder, create_agent
├── services/          # Service layer
│   ├── locator.py     # ServiceLocator pattern
│   ├── initialization.py # Service setup
│   └── llm_adapter.py # LLM service adapter
├── context/           # SDK context utilities
│   ├── formatter.py   # Context formatting
│   ├── types.py       # ToolContext type
│   └── type_manager.py # Type management
├── utils/             # Developer utilities
│   ├── coercion.py    # Type coercion
│   ├── errors.py      # Error handling
│   └── retry.py       # Retry logic
├── agents/            # Agent utilities (NOT runtime)
│   └── utils.py       # JSON extraction, parsing
├── config.py          # SDK configuration
├── decorators.py      # @tool decorator
└── exceptions.py      # SDK exceptions
```

## Service Locator Pattern

The SDK uses ServiceLocator to access orchestrator services without direct imports:

```python
from ice_sdk.services import ServiceLocator

# In tool implementation
async def execute(self, **kwargs):
    # Get services from orchestrator layer
    llm_service = ServiceLocator.get("llm_service")
    context_manager = ServiceLocator.get("context_manager")
    
    # Use services without importing from orchestrator
    result = await llm_service.generate(config, prompt)
```

## What Moved to Orchestrator

The following components now live in `ice_orchestrator` for proper separation of concerns:

- **Agent Runtime**: `AgentNode`, `MemoryAgent`, `AgentExecutor`
- **Memory Subsystem**: All memory implementations (working, episodic, semantic, etc.)
- **LLM Providers**: OpenAI, Anthropic, Gemini handlers and `LLMService`
- **Context Management**: `GraphContextManager`, workflow context, stores
- **LLM Operators**: Insights, summarizer, line item generator operators

## Development Patterns

### Creating Tools
1. Inherit from appropriate base class (`ToolBase`, `AITool`, `DataTool`)
2. Use `@tool` decorator for auto-registration
3. Implement `_execute_impl()` method
4. Access orchestrator services via `ServiceLocator`

### Building Agents
1. Use `AgentBuilder` or `create_agent()` to create configurations
2. Agent runtime execution happens in orchestrator layer
3. SDK provides configuration builders, not runtime

### Type Safety
```python
from ice_sdk.utils.coercion import safe_cast

# Coerce types safely
value = safe_cast(user_input, int, default=0)
```

## Testing
```bash
make test   # Run SDK tests
make type   # Type check with mypy --strict
```

## Key Design Principles

1. **Developer-Focused**: SDK provides tools for developers, not runtime
2. **Layer Boundaries**: Never import from orchestrator or API layers
3. **Service Pattern**: Use ServiceLocator for cross-layer dependencies
4. **Tool-Centric**: Primary focus is enabling tool development
5. **Type Safety**: Pydantic models and type hints throughout

## Migration Notes

If upgrading from previous versions:
- Import agents from `ice_orchestrator.agent` instead of `ice_sdk.agents`
- Import memory from `ice_orchestrator.memory` instead of `ice_sdk.memory`
- Use ServiceLocator.get("llm_service") instead of importing LLMService
- Unified registry is now in `ice_core.unified_registry`

## License
MIT 