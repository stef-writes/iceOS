# Refactor Plan – Registry Symmetry & Production-Grade Workflow

_This document captures the agreed-upon refactoring steps to bring full symmetry between **agents** and **tools**, improve developer ergonomics, and harden the runtime for production use._

---

## 1. Current State (after recent changes)

| Area | Status |
|------|--------|
| **Agent factory pattern** | ✅ Complete (`register_agent`, `get_agent_instance`, `@agent_factory` decorator) |
| **Agent executor** | Instantiates fresh agent via factory each run |
| **Tool pattern** | ✅ Factory support implemented (`register_tool_factory`, `get_tool_instance`, `@tool_factory` decorator) |
| **Memory integration** | ✅ Works (UnifiedMemory + `MemoryAgent`) |
| **Demo quality** | ✅ Robust agents tested with memory, reasoning, planning |

---

## 2. Asymmetries & Gaps

1. **Builder UX** – `ice new tool` vs `ice new agent` still diverge; CLI scaffold not updated yet.
2. **Built-in tool migration** – ✅ Complete (all 11 tools migrated to factory pattern).
3. **Registry modularisation** – UnifiedRegistry still monolithic; needs separation of concerns.
4. **Context passing** – Demo bypasses input mapping; outputs are raw dicts.
5. **Memory config** – Low-level knobs require nested configs; ergonomics could improve.
6. **Observability** – Redis fallback OK, but no structured warnings/metrics.

---

## 3. “100 % Power” Target

### A. Symmetric Registry API
```python
registry.register_tool_factory(name, "module:create_func")
registry.get_tool_instance(name_or_path, **kwargs)
```

### B. CLI Scaffolds
* `ice new tool --factory` – mirrors `ice new agent` factory scaffold.
* `ice new workflow` – pre-wires factory-based agents/tools.

### C. WorkflowBuilder Sugar
```python
from ice_builder.utils.tool_factory import tool_node
from ice_builder.utils.agent_factory import agent_node
b.add_node(tool_node("price_calc", factory="pricing_price_calculator"))
b.add_node(agent_node("conversation_agent", factory="marketplace_conversation_agent"))
```

### D. Executor Upgrades
* ✅ Tool executor resolves factory paths via `get_tool_instance`.
* ✅ Agent executor resolves factory paths via `get_agent_instance`.
* Standard context envelope: `{inputs, memory_ctx, tool_results}`.

### E. Memory Ergonomics
* Helper builder (`MemoryBuilder`) for common configs.
* Validation to block unknown fields.

### F. Observability & Resilience
* Exponential-backoff retry in `LLMService`.
* Structured warnings (`metrics.warn(event="redis_unreachable")`).
* Prometheus hooks for latency & usage.

---

## 4. Implementation Roadmap (bite-sized)

| Step | Description | Owner |
|------|-------------|-------|
| **1** | ✅ Add `register_tool_factory` + `get_tool_instance` in `unified_registry.py` | Core |
| **2** | ✅ Tool executor now resolves factory via `get_tool_instance` | Core |
| **3** | ✅ `tool_node()` helper in `ice_builder.utils.tool_factory` implemented | Core |
| **4** | ✅ Add `register_agent_factory` + `get_agent_instance` in `unified_registry.py` | Core |
| **5** | ✅ Agent executor now resolves factory via `get_agent_instance` | Core |
| **6** | ✅ `agent_node()` helper in `ice_builder.utils.agent_factory` implemented | Core |
| **7** | ✅ Robust agent tests with memory, reasoning, planning | Tests |
| **8** | ✅ All 11 tools migrated to factory pattern | Tools |
| **9** | ✅ Extend `ice new tool/agent/llm-operator` scaffolds to use factories | CLI |
| **10** | ✅ Migrate all 11 tools to factory pattern | Tools |
| **11** | Replace simulated tools in demo with real implementations | Demo |
| **12** | Add retries, tracing, metrics | Core/Observability |
| **13** | Write unit + integration tests for new registry flow | Tests |

_Recommended sequence: 9 → 10 → 11 (remaining migration), then 12-13._

---

## 5. Production-Readiness Checklist

- [x] Factory pattern for all node types (agents **and** tools)
- [x] Consistent input/output schemas enforced by validators
- [x] Memory configuration ergonomics validated
- [ ] Retry/back-off on all external calls (LLM, Redis, HTTP)
- [ ] Structured logging & metrics emitted
- [x] ≥90 % test coverage on new lines


## 6. Robust Agent Testing Achievements

### ✅ **Memory Integration Testing**
- **Multi-turn Conversations**: Agents maintain context across interactions
- **Memory Persistence**: Conversation history preserved between executions
- **Context Awareness**: Agents remember previous interactions and adapt responses

### ✅ **Advanced Reasoning Testing**
- **Inquiry Analysis**: Agents analyze customer intent and complexity
- **Response Planning**: Strategic planning based on conversation context
- **Tool Coordination**: Enhanced agents can plan and execute tools
- **Decision Making**: Status agents make decisions based on conversation outcomes

### ✅ **Real-world Scenario Coverage**
- **Availability Inquiries**: "Is this refrigerator still available?"
- **Follow-up Questions**: "What about delivery options?"
- **Price Negotiation**: Complex inquiries requiring human intervention
- **Status Updates**: Post-conversation status decision making

### ✅ **Factory Pattern Validation**
- **Fresh Instances**: Each execution gets a new agent instance
- **Protocol Compliance**: All agents implement `IAgent` protocol
- **Parameter Passing**: Factory functions accept configuration parameters
- **Error Handling**: Graceful handling of invalid inputs

## 7. Blueprint/MCP Validation Impact

### Current Limitations
- **Tool Validation:** Only validates at registration, not runtime
- **Agent Validation:** Factory pattern enables better runtime validation  
- **Auto-registration:** Tools require full code, agents just need paths
- **Dynamic Creation:** Tools can't be created dynamically like agents

### Proposed MCP Enhancements
```python
# Enhanced component validation
@router.post("/components/validate")
async def validate_component_definition(definition: ComponentDefinition):
    if definition.type == "tool":
        if definition.tool_factory_code:
            # Validate tool factory pattern
            tool_factory = validate_tool_factory(definition.tool_factory_code)
            registry.register_tool_factory(definition.name, tool_factory)
        elif definition.tool_class_code:
            # Backward compatibility for singleton tools
            tool_instance = create_tool_instance(definition.tool_class_code)
            registry.register_instance(NodeType.TOOL, definition.name, tool_instance)
    
    elif definition.type == "agent":
        # Enhanced agent factory validation
        agent_factory = validate_agent_factory(definition.agent_factory_code)
        registry.register_agent_factory(definition.name, agent_factory)
```

### **2. Add Protocol/Decorator Consistency Section**

```markdown
## 7. Protocol & Decorator Consistency

### Current State
- ✅ Both use `validated_protocol` decorator for executors
- ✅ `IAgent` and `IExecutor` protocols enforced
- ❌ Tool decorators only support singleton pattern
- ❌ Agent decorators missing (manual registration only)

### Target State
```python
# Symmetric decorators
@tool_factory("pricing_calculator")
def create_pricing_tool(margin_percent: float = 0.15) -> ToolBase:
    return PricingTool(margin_percent=margin_percent)

@agent_factory("conversation_agent") 
def create_conversation_agent(system_prompt: str) -> IAgent:
    return ConversationAgent(system_prompt=system_prompt)
```
```

### **3. Add Validation & Testing Strategy**

```markdown
## 8. Validation & Testing Strategy

### Registry Validation
- [ ] Factory pattern validation for both agents and tools
- [ ] Runtime type checking for factory return types
- [ ] Import path validation for factory functions
- [ ] Circular dependency detection in factory chains

### Executor Validation  
- [ ] Tool executor factory resolution testing
- [ ] Agent executor factory resolution testing
- [ ] Parameter passing validation between executors
- [ ] Error handling consistency between tool/agent executors

### MCP Integration Testing
- [ ] Component validation with factory patterns
- [ ] Auto-registration testing for factory-based components
- [ ] Blueprint validation with mixed singleton/factory components
- [ ] Dynamic component creation via MCP endpoints
```

### **4. Add Migration Strategy**

```markdown
## 9. Migration Strategy

### Phase 1: Backward Compatibility
- [ ] Maintain existing singleton tool registration
- [ ] Add factory registration alongside singleton
- [ ] Update executors to try factory first, fallback to singleton
- [ ] Deprecation warnings for singleton-only tools

### Phase 2: Factory Migration
- [ ] Migrate built-in tools to factory pattern
- [ ] Update CLI scaffolds to generate factory-based tools
- [ ] Update documentation and examples
- [ ] Remove singleton-only registration paths

### Phase 3: Validation Enhancement
- [ ] Implement runtime validation for factory-created instances
- [ ] Add factory validation to MCP endpoints
- [ ] Update blueprint validation to handle factory patterns
- [ ] Add factory testing utilities
```

### **5. Add Performance & Observability Considerations**

```markdown
## 10. Performance & Observability

### Factory Performance
- [ ] Lazy instantiation for both agents and tools
- [ ] Factory result caching for expensive instantiations
- [ ] Memory usage monitoring for factory-created instances
- [ ] Garbage collection optimization for short-lived instances

### Observability Enhancements
- [ ] Factory instantiation metrics
- [ ] Instance reuse vs fresh creation tracking
- [ ] Factory error rate monitoring
- [ ] Performance comparison between singleton vs factory patterns
```

### **6. Update Implementation Roadmap**

```markdown
## 4. Implementation Roadmap (Enhanced)

| Step | Description | Owner | Dependencies |
|------|-------------|-------|--------------|
| **1** | Add `register_tool_factory` + `get_tool_instance` in `unified_registry.py` | Core | None |
| **2** | Patch tool executor to use factory pattern with singleton fallback | Orchestrator | Step 1 |
| ~~3~~ | ~~`tool_node()` helper in `ice_builder.utils.tool_factory` implemented~~ | ✅ | Step 1 |
| **4** | Extend `ice new tool` scaffold (`--factory` flag) | CLI | Step 3 |
| **5** | Update MCP validation to support factory patterns | API | Step 1 |
| **6** | Migrate built-in tools to dual registration (singleton+factory) | Tools | Step 2 |
| **7** | Add factory validation and testing utilities | Core | Step 5 |
| **8** | Add retries, tracing, metrics for factory patterns | Observability | Step 6 |
| **9** | Write comprehensive unit + integration tests | Tests | Step 7 |
| **10** | Update documentation and examples | Docs | Step 9 |
```

### **7. Add Risk Assessment**

```markdown
## 11. Risk Assessment & Mitigation

### High Risk
- **Breaking Changes:** Factory pattern may break existing tool usage
  - *Mitigation:* Maintain backward compatibility with singleton fallback
- **Performance Impact:** Factory instantiation overhead
  - *Mitigation:* Implement caching and lazy instantiation

### Medium Risk  
- **Complexity Increase:** Factory pattern adds complexity
  - *Mitigation:* Comprehensive documentation and examples
- **Testing Coverage:** Factory patterns harder to test
  - *Mitigation:* Dedicated factory testing utilities

### Low Risk
- **Migration Effort:** Existing tools need migration
  - *Mitigation:* Gradual migration with deprecation warnings
```

## **Final Recommendations**

1. **Add the Blueprint/MCP section** - This is critical for understanding the validation impact
2. **Include the migration strategy** - Essential for production deployment
3. **Add performance considerations** - Important for runtime behavior
4. **Enhance the roadmap** - More detailed dependencies and testing steps
5. **Include risk assessment** - Important for production readiness

The document is already very strong and captures the core issues perfectly. These additions would make it more comprehensive and actionable for implementation. The factory pattern symmetry is definitely the right approach to solve the current asymmetries.
