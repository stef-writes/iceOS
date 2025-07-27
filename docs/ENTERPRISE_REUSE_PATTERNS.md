# Enterprise Reuse Patterns for iceOS Components

## 🎯 **Optimal Pattern for Tool/Agent Reuse**

This document outlines the enterprise-grade patterns for maximum component reusability across demos and early product builds.

## 📐 **Architecture Pattern**

```
use-cases/
├── YourDemo/
│   ├── __init__.py          # Export main components
│   ├── registry.py          # Centralized registration system  
│   ├── enterprise_demo.py   # Main demo with both MCP + SDK approaches
│   ├── tools/
│   │   ├── __init__.py      # Export all tools
│   │   ├── tool_a.py        # Individual tool implementations
│   │   └── tool_b.py
│   └── agents/
│       ├── __init__.py      # Export all agents
│       └── your_agent.py    # Agent implementations
```

## 🔧 **1. Component Structure Pattern**

### **Tools (Stateless Operations)**
```python
# tools/your_tool.py
from ice_sdk.tools.base import ToolBase

class YourTool(ToolBase):
    name: str = "your_tool"
    description: str = "What this tool does"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(self, param1: str, param2: int = 100, **kwargs):
        # Implementation here
        return {"success": True, "result": "output"}
```

### **Agents (Intelligent Reasoning)**
```python
# agents/your_agent.py
from ice_orchestrator.agent.memory import MemoryAgent

class YourAgent(MemoryAgent):
    async def _execute_with_memory(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Use self.memory for persistence
        # Use self.tools for external actions
        return {"response": "intelligent result"}
```

## 🏢 **2. Registration System Pattern**

### **Centralized Registry (registry.py)**
```python
# registry.py - Enterprise registration pattern
from ice_core.unified_registry import registry, global_agent_registry
from ice_core.models.enums import NodeType

# Import components
from tools.tool_a import ToolA
from tools.tool_b import ToolB  
from agents.your_agent import YourAgent

async def register_your_demo_components() -> Dict[str, Any]:
    """Enterprise-grade component registration."""
    
    print("🔧 Registering YourDemo components...")
    
    # Register tools
    tools = [ToolA(), ToolB()]
    tool_count = 0
    
    for tool in tools:
        try:
            registry.register_instance(NodeType.TOOL, tool.name, tool)
            print(f"   ✅ Registered tool: {tool.name}")
            tool_count += 1
        except Exception as e:
            print(f"   ❌ Failed to register tool {tool.name}: {e}")
    
    # Register agents
    agent_registrations = [
        ("your_agent", "use_cases.YourDemo.agents.your_agent")
    ]
    
    agent_count = 0
    for agent_name, agent_package in agent_registrations:
        try:
            global_agent_registry.register_agent(agent_name, agent_package)
            print(f"   ✅ Registered agent: {agent_name}")
            agent_count += 1
        except Exception as e:
            print(f"   ❌ Failed to register agent {agent_name}: {e}")
    
    return {
        "success": True,
        "tools_registered": tool_count,
        "agents_registered": agent_count,
        "total_components": tool_count + agent_count
    }

def get_component_registry() -> Dict[str, Any]:
    """Component discovery and documentation."""
    return {
        "tools": [{"name": "tool_a", "reusable": True}, ...],
        "agents": [{"name": "your_agent", "memory_enabled": True}, ...],
        "workflows": ["workflow_a", "workflow_b"]
    }
```

## 🚀 **3. Dual Execution Pattern**

### **Enterprise Demo Structure**
```python
# enterprise_demo.py - Both approaches in one demo
async def main():
    # Initialize environment
    await load_environment()
    from ice_orchestrator import initialize_orchestrator
    initialize_orchestrator()
    
    # Register components using enterprise pattern
    registration_result = await register_your_demo_components()
    
    # Method 1: SDK WorkflowBuilder (Developer Experience)
    sdk_result = await run_sdk_workflow_approach()
    
    # Method 2: MCP Blueprint (Enterprise Governance)  
    blueprint_result = await run_blueprint_approach()
    
    # Compare results
    print(f"SDK Workflow:  {'✅' if sdk_result.get('success') else '❌'}")
    print(f"MCP Blueprint: {'✅' if blueprint_result.get('success') else '❌'}")
```

## 🔄 **4. Reuse Across Demos**

### **Cross-Demo Component Sharing**
```python
# In any other demo
from use_cases.YourDemo import ToolA, ToolB, YourAgent
from use_cases.YourDemo.registry import register_your_demo_components

# Instant reuse in new demo
async def setup_new_demo():
    await register_your_demo_components()  # All components available
    
    # Use in new workflow
    workflow = (WorkflowBuilder("New Demo")
        .add_tool("existing_tool", "tool_a")  # Reuse existing tool
        .add_agent("smart_agent", "your_agent")  # Reuse existing agent
        .build()
    )
```

## 📊 **5. Early Product Integration**

### **Component Catalog Pattern**
```python
# product_catalog.py - For early product builds
AVAILABLE_COMPONENTS = {
    "document_processing": {
        "tools": ["document_parser", "intelligent_chunker", "semantic_search"],
        "agents": ["document_chat_agent"],
        "registry": "use_cases.DocumentAssistant.registry"
    },
    "marketplace_automation": {
        "tools": ["read_inventory_csv", "ai_enrichment", "facebook_publisher"],
        "agents": ["customer_service_agent", "pricing_agent"],
        "registry": "use_cases.RivaRidge.FB_Marketplace_Seller.enhanced_blueprint_demo"
    }
}

async def build_custom_product(required_components: List[str]):
    """Build custom product from reusable components."""
    for component_set in required_components:
        registry_module = AVAILABLE_COMPONENTS[component_set]["registry"]
        await import_and_register(registry_module)
```

## 🛡️ **6. WASM Integration Benefits**

### **Security & Monitoring**
```python
# All components now get:
# - Resource monitoring (CPU, memory)
# - Security isolation 
# - Execution limits
# - OpenTelemetry metrics
# - Error handling

# Example metrics available:
# - wasm_executions_total{component="document_parser"}
# - wasm_execution_duration{component="customer_service_agent"}
# - wasm_memory_usage{component="ai_enrichment"}
```

## 🎯 **Best Practices Summary**

1. **Centralized Registration** - One registration function per demo
2. **Clean Module Structure** - Tools and agents in separate directories  
3. **Dual Execution Support** - Both SDK and MCP approaches
4. **Component Discoverability** - Registry info for documentation
5. **Cross-Demo Reuse** - Import components from other demos
6. **Early Product Ready** - Component catalog for product builds
7. **Enterprise Security** - Selective WASM sandboxing for user code
8. **Proper Error Handling** - Graceful degradation patterns

## ✅ **Working Examples**

- **RivaRidge**: ✅ Full marketplace automation with agents, memory, HTTP calls
- **DocumentAssistant**: ✅ Enterprise chat-in-a-box with document processing
- **Both**: ✅ Cross-compatible, reusable, selectively secured, enterprise-ready 