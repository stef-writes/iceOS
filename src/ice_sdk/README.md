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

@tool  # Auto-registers as "data_processor"
class DataProcessor(ToolBase):
    """Process data files with validation."""
    
    name = "data_processor"
    description = "Processes data files with validation"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        file_path = kwargs["file_path"]
        # Process the file
        return {"processed": True, "rows": 100}
```

### AI-Powered Tools
```python
from ice_sdk.tools.base import ToolBase
from ice_sdk.services import ServiceLocator

@tool  # Auto-registers as "content_analyzer"
class ContentAnalyzer(ToolBase):
    """Analyze content using LLM via ServiceLocator."""
    
    name = "content_analyzer"
    description = "Analyzes content using AI"
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        content = kwargs["content"]
        
        # Get LLM service via ServiceLocator (not direct import)
        llm_service = ServiceLocator.get("llm_service")
        
        result = await llm_service.generate(
            {"model": "gpt-4", "temperature": 0.1},
            f"Analyze this content: {content}"
        )
        
        return {"analysis": result.text}
```

## Building Workflows with Fluent API

### Modern WorkflowBuilder Pattern

```python
from ice_sdk.builders import WorkflowBuilder
from ice_orchestrator.execution.executor import WorkflowExecutor

# Modern fluent API approach
workflow = (WorkflowBuilder("Data Analysis Pipeline")
    # Tools for external operations
    .add_tool("fetch", "http_request", url="https://api.example.com/data")
    .add_tool("process", "csv_processor", delimiter=",")
    
    # LLM for analysis
    .add_llm("analyze", "gpt-4", 
             prompt="Analyze this data: {{process.output}}")
    
    # Agent with memory capabilities
    .add_agent("insights", "insights_agent",
               tools=["trend_analyzer", "pattern_finder"],
               memory={
                   "enable_semantic": True,
                   "enable_procedural": True
               })
    
    # Connect the pipeline
    .connect("fetch", "process")
    .connect("process", "analyze")
    .connect("analyze", "insights")
    .build()
)

# Execute immediately
result = await WorkflowExecutor().execute(workflow, {"source": "quarterly_data"})
```

### All Node Types

| Method | Purpose | Example Usage |
|--------|---------|---------------|
| `add_tool()` | External operations | `.add_tool("parse", "pdf_parser", file="docs.pdf")` |
| `add_llm()` | Language models | `.add_llm("summarize", "gpt-4", "Summarize: {{input}}")` |
| `add_agent()` | Intelligent agents | `.add_agent("chat", "customer_agent", memory={...})` |
| `add_code()` | Python execution | `.add_code("calc", "result = x * 2", sandbox=True)` |
| `add_condition()` | Conditional flow | `.add_condition("check", "{{price}} > 100", [...])` |
| `add_loop()` | Batch processing | `.add_loop("each", "{{items}}", [...])` |
| `add_parallel()` | Concurrent tasks | `.add_parallel("multi", [[...], [...]])` |
| `add_recursive()` | Agent negotiation | `.add_recursive("negotiate", agent_package="pricing")` |

### Memory-Enabled Agents

```python
# Agent with full cognitive memory system
workflow = (WorkflowBuilder("Customer Service")
    .add_agent("service", "customer_service_agent",
               tools=["inquiry_responder", "order_lookup"],
               memory={
                   "enable_working": True,    # Active session state
                   "enable_episodic": True,   # Customer interaction history
                   "enable_semantic": True,   # Product knowledge base
                   "enable_procedural": True  # Successful response patterns
               })
    .build()

### Creating Tools
1. Inherit from `ToolBase` (simplified 2-level hierarchy)
2. Use `@tool` decorator for auto-registration  
3. Implement `_execute_impl()` method
4. Access orchestrator services via `ServiceLocator`

### Building Agents
1. Use `AgentBuilder` or `create_agent()` to create configurations
2. Agent runtime execution happens in orchestrator layer
3. SDK provides configuration builders, not runtime


## Migration Notes

If upgrading from previous versions:
- Import agents from `ice_orchestrator.agent` instead of `ice_sdk.agents`
- Import memory from `ice_orchestrator.memory` instead of `ice_sdk.memory`
- Use ServiceLocator.get("llm_service") instead of importing LLMService
- Unified registry is now in `ice_core.unified_registry`

## License
MIT 