# Agent Swarms Architecture for iceOS

## 🐝 **Current Status: Individual Agents → Swarm Enhancement**

iceOS currently implements sophisticated **individual agents** with memory, but not coordinated **agent swarms**. Here's how swarms would integrate naturally with our architecture.

## 🏗️ **Swarm Architecture Design**

### **1. SwarmNode - Orchestration Layer**

```python
from ice_core.base_node import BaseNode
from ice_orchestrator.agent.memory import MemoryAgent
from typing import Dict, List, Any, Optional

class SwarmNode(BaseNode):
    """Orchestrates multiple agents working together on complex tasks."""
    
    agents: List[AgentSpec]          # Agent definitions and roles
    coordination_strategy: str       # "consensus", "hierarchical", "marketplace"
    shared_memory_pool: str         # Shared knowledge space ID
    communication_protocol: str     # "broadcast", "direct", "async_queue"
    max_rounds: int = 10            # Maximum coordination rounds
    
    class AgentSpec(BaseModel):
        agent_type: str             # "analyst", "critic", "synthesizer", "executor"
        agent_config: AgentNodeConfig
        role_description: str       # "You are the data analyst specialist"
        output_schema: Dict[str, Any]  # What this agent produces
        input_dependencies: List[str]  # Which other agents it needs input from

async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute swarm coordination logic."""
    
    # 1. Initialize shared memory pool
    shared_memory = await self._init_shared_memory_pool()
    
    # 2. Instantiate all agents
    agents = await self._instantiate_agents()
    
    # 3. Execute coordination strategy
    if self.coordination_strategy == "consensus":
        return await self._consensus_coordination(agents, inputs, shared_memory)
    elif self.coordination_strategy == "hierarchical":
        return await self._hierarchical_coordination(agents, inputs, shared_memory)
    elif self.coordination_strategy == "marketplace":
        return await self._marketplace_coordination(agents, inputs, shared_memory)
```

### **2. Coordination Strategies**

#### **A. Consensus Coordination**
```python
async def _consensus_coordination(
    self, 
    agents: List[MemoryAgent], 
    inputs: Dict[str, Any],
    shared_memory: SharedMemoryPool
) -> Dict[str, Any]:
    """All agents work on the same problem, reach consensus."""
    
    round_num = 0
    proposals = []
    
    while round_num < self.max_rounds:
        round_results = []
        
        # All agents generate proposals
        for agent in agents:
            agent_input = {
                **inputs,
                "round": round_num,
                "previous_proposals": proposals,
                "shared_context": await shared_memory.get_context()
            }
            
            result = await agent.execute(agent_input)
            round_results.append({
                "agent_id": agent.id,
                "role": agent.role,
                "proposal": result["response"],
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", "")
            })
        
        # Check for consensus (configurable threshold)
        consensus = await self._check_consensus(round_results)
        if consensus["reached"]:
            return {
                "status": "consensus_reached",
                "final_result": consensus["agreed_proposal"],
                "rounds": round_num + 1,
                "participants": len(agents),
                "confidence": consensus["confidence"]
            }
        
        # Update shared memory with round results
        await shared_memory.store_round_results(round_num, round_results)
        proposals.extend(round_results)
        round_num += 1
    
    # No consensus reached - return best proposal
    best_proposal = max(round_results, key=lambda x: x["confidence"])
    return {
        "status": "no_consensus",
        "best_proposal": best_proposal,
        "rounds": self.max_rounds,
        "all_proposals": proposals
    }
```

#### **B. Hierarchical Coordination** 
```python
async def _hierarchical_coordination(
    self,
    agents: List[MemoryAgent],
    inputs: Dict[str, Any], 
    shared_memory: SharedMemoryPool
) -> Dict[str, Any]:
    """Agents work in hierarchy: specialists → synthesizer → decision_maker."""
    
    # Phase 1: Specialist agents work in parallel
    specialist_results = {}
    specialist_agents = [a for a in agents if a.role in ["analyst", "researcher", "critic"]]
    
    specialist_tasks = []
    for specialist in specialist_agents:
        task = specialist.execute({
            **inputs,
            "role_focus": specialist.role_description,
            "shared_context": await shared_memory.get_context()
        })
        specialist_tasks.append((specialist.role, task))
    
    # Wait for all specialists
    for role, task in specialist_tasks:
        result = await task
        specialist_results[role] = result
        await shared_memory.store_specialist_result(role, result)
    
    # Phase 2: Synthesizer combines specialist outputs
    synthesizer = next(a for a in agents if a.role == "synthesizer")
    synthesis = await synthesizer.execute({
        **inputs,
        "specialist_inputs": specialist_results,
        "task": "synthesize_specialist_findings"
    })
    
    # Phase 3: Decision maker makes final call
    decision_maker = next(a for a in agents if a.role == "decision_maker")
    final_decision = await decision_maker.execute({
        **inputs,
        "synthesis": synthesis,
        "specialist_findings": specialist_results,
        "task": "make_final_decision"
    })
    
    return {
        "status": "hierarchical_complete",
        "final_decision": final_decision,
        "synthesis": synthesis,
        "specialist_findings": specialist_results,
        "coordination_strategy": "hierarchical"
    }
```

#### **C. Marketplace Coordination**
```python
async def _marketplace_coordination(
    self,
    agents: List[MemoryAgent],
    inputs: Dict[str, Any],
    shared_memory: SharedMemoryPool
) -> Dict[str, Any]:
    """Agents bid on subtasks, coordinate via market mechanisms."""
    
    # 1. Task decomposition
    task_decomposer = next(a for a in agents if a.role == "task_decomposer")
    decomposition = await task_decomposer.execute({
        **inputs,
        "task": "decompose_into_subtasks"
    })
    
    subtasks = decomposition["subtasks"]
    completed_tasks = {}
    
    # 2. For each subtask, run auction
    for subtask in subtasks:
        # Agents bid on the subtask
        bids = []
        for agent in agents:
            if agent.role != "task_decomposer":
                bid = await agent.execute({
                    "subtask": subtask,
                    "task": "evaluate_and_bid",
                    "completed_tasks": completed_tasks
                })
                
                bids.append({
                    "agent_id": agent.id,
                    "role": agent.role,
                    "bid_confidence": bid.get("confidence", 0.0),
                    "estimated_quality": bid.get("estimated_quality", 0.0),
                    "reasoning": bid.get("reasoning", "")
                })
        
        # Award task to highest bidder
        winner = max(bids, key=lambda x: x["bid_confidence"] * x["estimated_quality"])
        winning_agent = next(a for a in agents if a.id == winner["agent_id"])
        
        # Execute subtask
        result = await winning_agent.execute({
            "subtask": subtask,
            "task": "execute_subtask", 
            "context": await shared_memory.get_context()
        })
        
        completed_tasks[subtask["id"]] = {
            "result": result,
            "executor": winner["agent_id"],
            "execution_quality": result.get("quality_score", 0.0)
        }
        
        await shared_memory.store_subtask_result(subtask["id"], completed_tasks[subtask["id"]])
    
    # 3. Final integration
    integrator = next(a for a in agents if a.role == "integrator")
    final_result = await integrator.execute({
        **inputs,
        "completed_subtasks": completed_tasks,
        "task": "integrate_results"
    })
    
    return {
        "status": "marketplace_complete",
        "final_result": final_result,
        "subtask_results": completed_tasks,
        "coordination_strategy": "marketplace"
    }
```

### **3. Shared Memory Pool**

```python
class SharedMemoryPool:
    """Shared knowledge space for agent coordination."""
    
    def __init__(self, pool_id: str, redis_client: Any):
        self.pool_id = pool_id
        self.redis = redis_client
        self.namespace = f"swarm:memory:{pool_id}"
    
    async def store_round_results(self, round_num: int, results: List[Dict]):
        """Store results from a coordination round."""
        key = f"{self.namespace}:round:{round_num}"
        await self.redis.set(key, json.dumps(results), ex=3600)  # 1 hour TTL
    
    async def get_context(self) -> Dict[str, Any]:
        """Get shared context for agents."""
        keys = await self.redis.keys(f"{self.namespace}:*")
        context = {}
        
        for key in keys:
            data = await self.redis.get(key)
            if data:
                context[key.split(":")[-1]] = json.loads(data)
        
        return context
    
    async def store_specialist_result(self, role: str, result: Dict):
        """Store specialist agent result."""
        key = f"{self.namespace}:specialist:{role}"
        await self.redis.set(key, json.dumps(result), ex=3600)
    
    async def broadcast_message(self, message: Dict, sender_id: str):
        """Broadcast message to all agents in swarm."""
        channel = f"{self.namespace}:broadcast"
        await self.redis.publish(channel, json.dumps({
            "sender": sender_id,
            "timestamp": time.time(),
            "message": message
        }))
```

### **4. Integration with Existing Architecture**

#### **Workflow Integration**
```python
# In your workflow definition
workflow = (WorkflowBuilder("Multi-Agent Analysis")
    # Data preparation
    .add_tool("load_data", "csv_reader", file_path="analysis_data.csv")
    .add_tool("clean_data", "data_cleaner")
    
    # Agent swarm analysis
    .add_swarm("analysis_swarm", {
        "agents": [
            {"role": "data_analyst", "type": "statistical_agent"},
            {"role": "trend_analyst", "type": "time_series_agent"}, 
            {"role": "anomaly_detector", "type": "outlier_agent"},
            {"role": "synthesizer", "type": "synthesis_agent"}
        ],
        "coordination_strategy": "hierarchical",
        "max_rounds": 5
    })
    
    # Post-processing
    .add_tool("generate_report", "report_generator")
    
    .connect("load_data", "clean_data")
    .connect("clean_data", "analysis_swarm")
    .connect("analysis_swarm", "generate_report")
    .build()
)
```

#### **MCP Blueprint Integration**
```json
{
  "blueprint_id": "agent_swarm_analysis",
  "nodes": [
    {
      "id": "market_analysis_swarm",
      "type": "swarm",
      "swarm_config": {
        "coordination_strategy": "consensus",
        "agents": [
          {
            "role": "market_researcher",
            "package": "use_cases.MarketAnalysis.agents.market_researcher",
            "role_description": "Analyze market trends and opportunities"
          },
          {
            "role": "competitive_analyst", 
            "package": "use_cases.MarketAnalysis.agents.competitive_analyst",
            "role_description": "Assess competitive landscape"
          },
          {
            "role": "risk_analyst",
            "package": "use_cases.MarketAnalysis.agents.risk_analyst", 
            "role_description": "Identify and assess risks"
          }
        ],
        "shared_memory_pool": "market_analysis_pool",
        "max_rounds": 8,
        "consensus_threshold": 0.75
      }
    }
  ]
}
```

## 🎯 **Implementation Priority**

### **Phase 1: Basic Swarm Coordination (2-3 weeks)**
- SwarmNode base implementation
- Consensus coordination strategy
- Basic shared memory pool
- Integration with existing agent framework

### **Phase 2: Advanced Strategies (1 month)**
- Hierarchical coordination
- Marketplace coordination  
- Enhanced communication protocols
- Performance optimization

### **Phase 3: Production Features (1 month)**
- Swarm monitoring and observability
- Dynamic agent scaling
- Fault tolerance and recovery
- Enterprise governance

## 🏆 **Competitive Advantages**

1. **Selective Security**: Agent code uses direct execution; user code is WASM sandboxed
2. **Unified Memory**: Sophisticated memory integration across agents
3. **Enterprise Ready**: Built-in observability, governance, scaling
4. **Multiple Strategies**: Support for consensus, hierarchical, and marketplace coordination
5. **Tool Integration**: Agents can coordinate tool usage across the swarm
6. **MCP Integration**: Visual swarm design and monitoring via Canvas

This architecture leverages iceOS's existing strengths while adding powerful multi-agent capabilities! 🚀 