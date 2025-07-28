# Recursive Flows in iceOS

## 🚀 **Introduction**

iceOS now supports **recursive workflows** - a breakthrough capability that enables agent conversations to continue until convergence. This puts iceOS **on par with LangGraph** while maintaining all enterprise production features.

## 🎯 **What Are Recursive Flows?**

Recursive flows allow workflows to loop back on themselves with intelligent convergence detection:

```python
# Traditional DAG (one-way only)
User → Agent A → Agent B → End

# Recursive Flow (back-and-forth until convergence)  
User → Agent A ↔ Agent B → Convergence → End
             ↑_____↓ (until agreement)
```

## 🏗️ **Core Components**

### **1. RecursiveNodeConfig**

The heart of recursive flows - a new node type that enables controlled cycles:

```python
from ice_core.models import RecursiveNodeConfig

recursive_config = RecursiveNodeConfig(
    id="negotiation_loop",
    type="recursive",
    agent_package="agents.negotiator",           # Agent to execute recursively
    recursive_sources=["buyer", "seller"],       # Nodes that can trigger recursion
    convergence_condition="deal_agreed == True", # Stop condition
    max_iterations=15,                          # Safety limit
    preserve_context=True,                      # Keep context across iterations
    context_key="negotiation_context"          # Context storage key
)
```

### **2. Enhanced Cycle Detection**

Smart analysis that allows intentional cycles while blocking unintended ones:

```python
# The system automatically:
# ✅ Allows cycles involving RecursiveNodeConfig
# ❌ Blocks cycles not properly declared
# 🛡️ Validates recursive_sources are correctly specified
```

### **3. Convergence Detection**

Safe expression evaluation to determine when to stop recursion:

```python
# Examples of convergence conditions
"agreement_reached == True"              # Boolean flag
"price_gap < 50"                        # Numeric threshold  
"consensus_score >= 0.95"               # Percentage threshold
"iteration_count >= max_attempts"       # Iteration-based
```

## 🛠️ **Building Recursive Workflows**

### **Using WorkflowBuilder**

The simplest way to create recursive workflows:

```python
from ice_sdk.builders.workflow import WorkflowBuilder

# Create a negotiation workflow
workflow = (WorkflowBuilder("Agent Negotiation")
    
    # Initial agents
    .add_agent("buyer", "agents.buyer_agent")
    .add_agent("seller", "agents.seller_agent")
    
    # Recursive conversation loop
    .add_recursive(
        "negotiation_loop",
        agent_package="agents.coordinator",
        recursive_sources=["buyer", "seller"],
        convergence_condition="deal_agreed == True",
        max_iterations=20,
        preserve_context=True
    )
    
    # Connect the flow
    .connect("buyer", "negotiation_loop")
    .connect("seller", "negotiation_loop")
    
    .build()
)

# Execute the workflow
result = await workflow.execute()
```

### **Direct Configuration**

For advanced use cases, configure recursion directly:

```python
from ice_core.models import RecursiveNodeConfig, AgentNodeConfig

# Create agents
buyer = AgentNodeConfig(id="buyer", package="agents.buyer")
seller = AgentNodeConfig(id="seller", package="agents.seller")

# Create recursive coordinator
recursive_node = RecursiveNodeConfig(
    id="negotiation",
    agent_package="agents.coordinator",
    recursive_sources=["buyer", "seller"],
    convergence_condition="consensus >= 0.8",
    max_iterations=25,
    preserve_context=True,
    
    # Advanced options
    context_key="conversation_memory",
    dependencies=["buyer", "seller"]
)
```

## 📋 **Configuration Options**

### **Required Fields**

| Field | Description | Example |
|-------|-------------|---------|
| `id` | Unique node identifier | `"negotiation_loop"` |
| `type` | Must be `"recursive"` | `"recursive"` |
| `recursive_sources` | Nodes that can trigger recursion | `["buyer", "seller"]` |
| `agent_package` OR `workflow_ref` | What to execute recursively | `"agents.coordinator"` |

### **Optional Fields**

| Field | Default | Description |
|-------|---------|-------------|
| `convergence_condition` | `None` | Expression to stop recursion |
| `max_iterations` | `50` | Safety limit for iterations |
| `preserve_context` | `True` | Keep context across iterations |
| `context_key` | `"recursive_context"` | Key for context storage |

### **Safety Features**

- **Max Iterations**: Automatic stop at iteration limit
- **Safe Evaluation**: Convergence conditions evaluated in sandboxed environment
- **Error Handling**: Graceful failure with detailed error messages
- **Resource Monitoring**: Memory and execution time tracking

## 🎯 **Use Cases**

### **1. Agent Negotiations**

Multi-turn bargaining until agreement:

```python
workflow = (WorkflowBuilder("Product Negotiation")
    .add_agent("buyer", "marketplace.buyer_agent", target_price=800)
    .add_agent("seller", "marketplace.seller_agent", min_price=750)
    
    .add_recursive(
        "negotiation",
        agent_package="marketplace.negotiation_coordinator",
        recursive_sources=["buyer", "seller"],
        convergence_condition="price_agreed == True",
        max_iterations=15
    )
    
    .build()
)
```

### **2. Consensus Building**

Team agents working toward shared decisions:

```python
workflow = (WorkflowBuilder("Team Decision")
    .add_agent("expert1", "experts.domain_expert")
    .add_agent("expert2", "experts.technical_expert") 
    .add_agent("expert3", "experts.business_expert")
    
    .add_recursive(
        "consensus_building",
        agent_package="coordination.consensus_coordinator",
        recursive_sources=["expert1", "expert2", "expert3"],
        convergence_condition="consensus_score >= 0.85",
        max_iterations=20
    )
    
    .build()
)
```

### **3. Iterative Refinement**

Continuous improvement loops:

```python
workflow = (WorkflowBuilder("Content Refinement")
    .add_agent("writer", "content.writer_agent")
    .add_agent("reviewer", "content.reviewer_agent")
    
    .add_recursive(
        "refinement_loop",
        agent_package="content.refinement_coordinator",
        recursive_sources=["writer", "reviewer"],
        convergence_condition="quality_score >= 0.95",
        max_iterations=10
    )
    
    .build()
)
```

## 🔧 **Implementation Details**

### **Execution Flow**

1. **Initial Execution**: Recursive node executes configured agent/workflow
2. **Context Enhancement**: Adds recursive metadata to context
3. **Convergence Check**: Evaluates convergence condition if specified
4. **Iteration Decision**: Determines whether to continue or stop
5. **Recursive Execution**: If continuing, triggers recursive sources
6. **Safety Monitoring**: Tracks iterations against max_iterations

### **Context Management**

Recursive flows automatically manage context across iterations:

```python
# Context automatically includes:
{
    "_recursive_iteration": 3,           # Current iteration number
    "_can_recurse": True,               # Whether recursion can continue
    "_recursive_node_id": "negotiation", # ID of recursive node
    "recursive_context": {              # Preserved context
        "iteration": 3,
        "node_id": "negotiation",
        # ... your custom context
    }
}
```

### **Memory Efficiency**

- **Context Reuse**: Efficient sharing of context across iterations
- **Memory Monitoring**: Automatic tracking of memory usage
- **Garbage Collection**: Cleanup of unused iteration data

## 📊 **Monitoring & Observability**

### **Metrics**

Recursive flows provide comprehensive metrics:

```python
# Available metrics
{
    "total_iterations": 7,
    "convergence_achieved": True,
    "convergence_reason": "condition_met",
    "execution_time": 12.34,
    "memory_usage": 45.6,
    "context_preservation_rate": 0.98
}
```

### **Events**

Real-time events for monitoring:

```python
# Event types
"recursive.iteration.started"     # New iteration beginning
"recursive.iteration.completed"   # Iteration finished
"recursive.convergence.achieved"  # Convergence reached
"recursive.max_iterations.reached" # Safety limit hit
"recursive.error.occurred"        # Error in recursive execution
```

## 🔒 **Security Considerations**

### **Safe Expression Evaluation**

Convergence conditions are evaluated in a restricted environment:

```python
# Allowed in convergence conditions
safe_globals = {
    '__builtins__': {},
    'True': True, 'False': False, 'None': None,
    'and': lambda a, b: a and b,
    'or': lambda a, b: a or b,
    'not': lambda x: not x,
    # Plus all context variables
}
```

### **Resource Limits**

- **Iteration Limits**: Prevent infinite loops
- **Memory Limits**: Configurable memory usage caps
- **Time Limits**: Execution time restrictions
- **Context Size Limits**: Prevent memory bloat

## 🚀 **Migration Guide**

### **From DAG-Only Workflows**

Converting existing workflows to use recursive flows:

```python
# Before: Traditional DAG
workflow = (WorkflowBuilder("Old Style")
    .add_agent("agent1", "package1")
    .add_agent("agent2", "package2")
    .connect("agent1", "agent2")
    .build()
)

# After: Recursive Flow
workflow = (WorkflowBuilder("New Style")
    .add_agent("agent1", "package1")
    .add_agent("agent2", "package2")
    
    # Add recursive conversation
    .add_recursive(
        "conversation",
        agent_package="coordinator",
        recursive_sources=["agent1", "agent2"],
        convergence_condition="task_complete == True"
    )
    
    .connect("agent1", "conversation")
    .connect("agent2", "conversation")
    .build()
)
```

### **Backward Compatibility**

- ✅ **All existing workflows continue to work unchanged**
- ✅ **No breaking changes to existing APIs**
- ✅ **Gradual adoption - add recursion only where needed**
- ✅ **Full interoperability between recursive and non-recursive nodes**

## 🏆 **Comparison with LangGraph**

| Feature | LangGraph | iceOS (Before) | iceOS (Now) |
|---------|-----------|----------------|-------------|
| **Recursive Flows** | ✅ Full | ❌ None | ✅ **Full** |
| **Convergence Detection** | ✅ Basic | ❌ None | ✅ **Enhanced** |
| **Context Preservation** | ✅ Basic | ✅ Good | ✅ **Enterprise** |
| **Safety Features** | ❌ Limited | ✅ Good | ✅ **Enterprise** |
| **Type Safety** | ❌ Limited | ✅ Strict | ✅ **Strict** |
| **Observability** | ❌ Basic | ✅ Full | ✅ **Full** |
| **Enterprise Features** | ❌ None | ✅ Advanced | ✅ **Advanced** |

## 📚 **Examples**

### **Complete Working Example**

```python
#!/usr/bin/env python3
"""Complete recursive workflow example."""

import asyncio
from ice_sdk.builders.workflow import WorkflowBuilder

async def main():
    # Build recursive negotiation workflow
    workflow = (WorkflowBuilder("Agent Negotiation")
        
        # Setup initial positions
        .add_agent("buyer", "demo.buyer_agent", target_price=800)
        .add_agent("seller", "demo.seller_agent", min_price=750)
        
        # Recursive conversation until agreement
        .add_recursive(
            "negotiation_loop",
            agent_package="demo.negotiation_coordinator",
            recursive_sources=["buyer", "seller"],
            convergence_condition="deal_agreed == True",
            max_iterations=15,
            preserve_context=True
        )
        
        # Final summary
        .add_agent("summarizer", "demo.deal_summarizer")
        
        # Connect the flow
        .connect("buyer", "negotiation_loop")
        .connect("seller", "negotiation_loop")
        .connect("negotiation_loop", "summarizer")
        
        .build()
    )
    
    # Execute with monitoring
    print("🚀 Starting recursive negotiation...")
    result = await workflow.execute()
    
    if result.success:
        print("✅ Negotiation completed successfully!")
        print(f"📊 Result: {result.output}")
    else:
        print(f"❌ Negotiation failed: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔮 **Future Enhancements**

- **Visual Editor**: Canvas-based design for recursive flows
- **Flow Templates**: Pre-built recursive patterns
- **Advanced Analytics**: ML-based convergence prediction
- **Distributed Recursion**: Multi-node recursive execution
- **Dynamic Conditions**: Runtime convergence condition updates

---

**🎉 Recursive flows represent a major breakthrough for iceOS, delivering LangGraph-level capabilities while maintaining enterprise-grade reliability, security, and observability!** 