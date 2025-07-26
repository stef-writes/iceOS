# Node-to-Node Protocol Architecture

This document explains iceOS's protocol-based architecture for node execution, which ensures clean separation of concerns, eliminates abstract method issues, and provides proper layer isolation.

## Overview

iceOS uses a sophisticated protocol-based system where **executors delegate to registered components** rather than manually instantiating node wrapper classes. This approach provides:

- **Clean Architecture**: Clear separation between orchestration and implementation
- **Protocol Compliance**: All components implement well-defined interfaces
- **Registry Pattern**: Centralized discovery and lifecycle management
- **No Abstract Method Issues**: Eliminates instantiation problems with incomplete classes
- **Service Isolation**: Each layer uses appropriate services and registries

## Architecture Layers

### 1. Core Protocols (`ice_core.protocols`)

**Purpose**: Define contracts between layers without implementations.

```python
# ice_core/protocols/tool.py
class ITool(Protocol):
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]: ...
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]: ...
    
    @classmethod  
    def get_output_schema(cls) -> Dict[str, Any]: ...

# ice_core/protocols/node.py
class INode(ABC):
    async def validate(self) -> None: ...
    async def execute(self, inputs: Dict[str, Any]) -> NodeExecutionResult: ...
    
    @property
    def input_schema(self) -> Dict[str, Any]: ...
    
    @property
    def output_schema(self) -> Dict[str, Any]: ...
```

### 2. Registry System (`ice_sdk.unified_registry`)

**Purpose**: Centralized component discovery and lifecycle management.

```python
# Register tools, agents, workflows, etc.
registry.register_instance(NodeType.TOOL, "csv_reader", csv_tool)
registry.register_instance(NodeType.AGENT, "analyst", analyst_agent)

# Retrieve for execution
tool = registry.get_instance(NodeType.TOOL, "csv_reader")
agent = registry.get_instance(NodeType.AGENT, "analyst")
```

### 3. Service Locator (`ice_sdk.services.locator`)

**Purpose**: Cross-layer service dependency injection.

```python
# Services register themselves on startup
ServiceLocator.register("llm_service", LLMService())
ServiceLocator.register("tool_service", ToolService())

# Executors retrieve services as needed
llm_service = ServiceLocator.get("llm_service")
```

## Protocol-Based Executor Pattern

### ❌ **OLD: Manual Instantiation (Anti-Pattern)**

```python
# src/ice_orchestrator/execution/executors/old_approach.py
@register_node("tool")
async def tool_executor(chain, cfg, ctx):
    # PROBLEM: Manual instantiation bypasses protocols
    node = ToolNode(tool_ref=cfg.tool_ref, tool_args=cfg.tool_args)
    return await node.execute(ctx)  # Abstract method errors!
```

**Problems with this approach:**
- Creates wrapper classes that serve no purpose
- Bypasses the registry system completely  
- Causes abstract method instantiation errors
- Tight coupling between orchestrator and implementation details
- No protocol compliance verification

### ✅ **NEW: Protocol-Based Delegation (Correct Pattern)**

```python
# src/ice_orchestrator/execution/executors/unified.py
@register_node("tool")  
async def tool_executor(chain, cfg, ctx):
    # SOLUTION: Use registry to get registered tool
    tool = registry.get_instance(NodeType.TOOL, cfg.tool_name)
    
    # Merge configuration with runtime context
    merged_inputs = {**cfg.tool_args, **ctx}
    
    # Delegate to ITool protocol
    output = await tool.execute(merged_inputs)
    
    # Build proper result metadata
    return NodeExecutionResult(
        success=True,
        output=output,
        metadata=NodeMetadata(...),
        execution_time=duration
    )
```

**Benefits of this approach:**
- Direct delegation to protocol-compliant components
- Registry-based discovery enables loose coupling
- No abstract method issues (tools are concrete implementations)
- Proper error handling and metadata generation
- Clean separation of orchestration vs. execution logic

## Executor Implementations

### Tool Executor

**Protocol**: `ITool`  
**Registry Lookup**: `NodeType.TOOL`  
**Pattern**: Direct delegation to registered tool instances

```python
async def tool_executor(chain, cfg, ctx):
    # Get tool from registry (implements ITool)
    tool = registry.get_instance(NodeType.TOOL, cfg.tool_name)
    
    # Execute using ITool.execute() protocol
    output = await tool.execute({**cfg.tool_args, **ctx})
    
    return NodeExecutionResult(...)
```

### LLM Executor

**Service**: `LLMService`  
**Pattern**: Direct service usage, no wrapper classes

```python
async def llm_executor(chain, cfg, ctx):
    # Use LLM service directly (no wrapper needed)
    llm_service = LLMService()
    
    # Render prompt template with context
    prompt = cfg.prompt_template.format(**ctx)
    
    # Execute via service
    text, usage, error = await llm_service.generate(
        llm_config=LLMConfig(...),
        prompt=prompt
    )
    
    return NodeExecutionResult(...)
```

### Agent Executor

**Protocol**: `IAgent` (future)  
**Registry Lookup**: `NodeType.AGENT`  
**Pattern**: Registry delegation for agent orchestration

```python
async def agent_executor(chain, cfg, ctx):
    # Get agent from registry
    agent = registry.get_instance(NodeType.AGENT, cfg.agent_ref)
    
    # Execute agent workflow
    output = await agent.execute(ctx)
    
    return NodeExecutionResult(...)
```

## Component Registration

### Tools Registration

```python
# In tool modules or initialization
from ice_sdk.unified_registry import registry
from ice_core.models.enums import NodeType

# Register tool instances
registry.register_instance(
    NodeType.TOOL, 
    "csv_reader", 
    CSVReaderTool()
)

registry.register_instance(
    NodeType.TOOL,
    "http_request", 
    HTTPRequestTool()
)
```

### Service Registration

```python
# In main.py or service initialization
from ice_sdk.services.locator import ServiceLocator

ServiceLocator.register("llm_service", LLMService())
ServiceLocator.register("tool_service", ToolService())
ServiceLocator.register("context_manager", GraphContextManager())
```

## Testing Protocol Compliance

### Unit Testing

```python
class TestProtocolCompliance:
    def test_tool_implements_itool_protocol(self):
        tool = CSVReaderTool()
        
        # Verify protocol methods exist
        assert hasattr(tool, 'execute')
        assert hasattr(tool, 'get_input_schema')
        assert hasattr(tool, 'get_output_schema')
        
        # Verify they're callable
        assert callable(tool.execute)
        assert callable(tool.get_input_schema)
        assert callable(tool.get_output_schema)
```

### Integration Testing

```python
class TestExecutorProtocolUsage:
    async def test_tool_executor_uses_registry(self):
        # Register mock tool
        mock_tool = Mock()
        registry.register_instance(NodeType.TOOL, "test_tool", mock_tool)
        
        # Execute via protocol
        result = await tool_executor(chain, config, context)
        
        # Verify registry was used
        mock_tool.execute.assert_called_once()
```

## Migration Guide

### For Existing Tools

1. **Ensure Protocol Compliance**: Verify your tool implements `ITool`
2. **Register in Registry**: Use `registry.register_instance()`
3. **Remove Manual Instantiation**: Delete any `ToolNode` wrapper usage
4. **Update Tests**: Test against registry pattern

### For New Components

1. **Start with Protocol**: Implement appropriate protocol (`ITool`, `IAgent`, etc.)
2. **Design for Registry**: Make components discoverable and reusable
3. **Avoid Wrapper Classes**: Connect directly to the execution system
4. **Write Protocol Tests**: Verify compliance with interfaces

## Best Practices

### DO ✅

- **Use registry lookup** for component discovery
- **Implement protocols** for all executable components  
- **Register instances** in appropriate lifecycle hooks
- **Test protocol compliance** in unit tests
- **Use service locator** for cross-layer dependencies

### DON'T ❌

- **Manually instantiate** node wrapper classes in executors
- **Bypass the registry** for component discovery
- **Create unnecessary wrapper classes** around working components
- **Mix orchestration logic** with implementation details
- **Import across layer boundaries** inappropriately

## Troubleshooting

### Common Issues

**"Abstract method not implemented"**
- **Cause**: Trying to instantiate incomplete node classes
- **Solution**: Use registry to get concrete implementations

**"Component not found in registry"** 
- **Cause**: Tool/agent not registered during initialization
- **Solution**: Ensure proper registration in startup sequence

**"Service not available"**
- **Cause**: Service not registered in ServiceLocator  
- **Solution**: Check service initialization order

### Debugging Tools

```python
# Check registry contents
from ice_sdk.unified_registry import registry
print(registry.list_nodes(NodeType.TOOL))

# Check service registration
from ice_sdk.services.locator import ServiceLocator  
print(ServiceLocator._services.keys())

# Verify executor registration
print(registry._executors.keys())
```

## Future Enhancements

- **Auto-discovery**: Automatic component registration via decorators
- **Protocol Validation**: Runtime verification of protocol compliance
- **Enhanced Registry**: Versioning, dependencies, lifecycle management
- **Service Mesh**: Advanced service discovery and communication patterns 