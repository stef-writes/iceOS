# Factory Pattern Extension TODO

## 🎯 **Current Status**
✅ **COMPLETE**: Tools and Agents use factory pattern
✅ **COMPLETE**: CLI scaffolds generate factory-based code
✅ **COMPLETE**: All 11 tools migrated to factory pattern
✅ **COMPLETE**: Demos updated to use factory pattern

## 📋 **TODO: Extend Factory Pattern to All Node Types**

### **Priority 1: Core Node Types (High Impact)**

#### **LLM Operators**
- [ ] Add `register_llm_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_llm_instance(name, **kwargs)` to unified_registry.py
- [ ] Update LLM executor to use factory pattern
- [ ] Migrate existing LLM operators to factory pattern
- [ ] Update CLI scaffold for LLM operators (already done ✅)

#### **Workflows**
- [ ] Add `register_workflow_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_workflow_instance(name, **kwargs)` to unified_registry.py
- [ ] Update workflow executor to use factory pattern
- [ ] Migrate existing workflows to factory pattern
- [ ] Add CLI scaffold for workflows

### **Priority 2: Control Flow Node Types**

#### **Conditions**
- [ ] Add `register_condition_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_condition_instance(name, **kwargs)` to unified_registry.py
- [ ] Update condition executor to use factory pattern
- [ ] Migrate existing conditions to factory pattern

#### **Loops**
- [ ] Add `register_loop_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_loop_instance(name, **kwargs)` to unified_registry.py
- [ ] Update loop executor to use factory pattern
- [ ] Migrate existing loops to factory pattern

#### **Parallel**
- [ ] Add `register_parallel_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_parallel_instance(name, **kwargs)` to unified_registry.py
- [ ] Update parallel executor to use factory pattern
- [ ] Migrate existing parallel nodes to factory pattern

### **Priority 3: Advanced Node Types**

#### **Recursive**
- [ ] Add `register_recursive_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_recursive_instance(name, **kwargs)` to unified_registry.py
- [ ] Update recursive executor to use factory pattern
- [ ] Migrate existing recursive nodes to factory pattern

#### **Code**
- [ ] Add `register_code_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_code_instance(name, **kwargs)` to unified_registry.py
- [ ] Update code executor to use factory pattern
- [ ] Migrate existing code nodes to factory pattern

#### **Human**
- [ ] Add `register_human_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_human_instance(name, **kwargs)` to unified_registry.py
- [ ] Update human executor to use factory pattern
- [ ] Migrate existing human nodes to factory pattern

#### **Monitor**
- [ ] Add `register_monitor_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_monitor_instance(name, **kwargs)` to unified_registry.py
- [ ] Update monitor executor to use factory pattern
- [ ] Migrate existing monitor nodes to factory pattern

#### **Swarm**
- [ ] Add `register_swarm_factory(name, import_path)` to unified_registry.py
- [ ] Add `get_swarm_instance(name, **kwargs)` to unified_registry.py
- [ ] Update swarm executor to use factory pattern
- [ ] Migrate existing swarm nodes to factory pattern

### **Priority 4: Infrastructure & Cleanup**

#### **Registry Cleanup**
- [ ] Remove deprecated `register_instance` method (after all migrations)
- [ ] Remove deprecated `get_instance` method (after all migrations)
- [ ] Update all tests to use factory pattern
- [ ] Update all documentation to reflect factory pattern

#### **CLI Scaffolds**
- [ ] Add `ice new condition` scaffold
- [ ] Add `ice new loop` scaffold
- [ ] Add `ice new parallel` scaffold
- [ ] Add `ice new recursive` scaffold
- [ ] Add `ice new code` scaffold
- [ ] Add `ice new human` scaffold
- [ ] Add `ice new monitor` scaffold
- [ ] Add `ice new swarm` scaffold
- [ ] Add `ice new workflow` scaffold

#### **Builder Sugar**
- [ ] Add `condition_node()` helper
- [ ] Add `loop_node()` helper
- [ ] Add `parallel_node()` helper
- [ ] Add `recursive_node()` helper
- [ ] Add `code_node()` helper
- [ ] Add `human_node()` helper
- [ ] Add `monitor_node()` helper
- [ ] Add `swarm_node()` helper
- [ ] Add `workflow_node()` helper

#### **Documentation**
- [ ] Update all README files
- [ ] Update architecture documentation
- [ ] Update API documentation
- [ ] Create factory pattern migration guide

## 🎯 **Implementation Strategy**

### **Phase 1: Core Node Types (Week 1)**
1. LLM Operators (high usage)
2. Workflows (high usage)

### **Phase 2: Control Flow (Week 2)**
1. Conditions
2. Loops
3. Parallel

### **Phase 3: Advanced Nodes (Week 3)**
1. Recursive
2. Code
3. Human
4. Monitor
5. Swarm

### **Phase 4: Cleanup (Week 4)**
1. Remove deprecated methods
2. Update all tests
3. Update all documentation

## 📊 **Current Factory Pattern Coverage**

| Node Type | Status | Priority |
|-----------|--------|----------|
| **Tool** | ✅ Complete | N/A |
| **Agent** | ✅ Complete | N/A |
| **LLM** | ☐ Pending | High |
| **Workflow** | ☐ Pending | High |
| **Condition** | ☐ Pending | Medium |
| **Loop** | ☐ Pending | Medium |
| **Parallel** | ☐ Pending | Medium |
| **Recursive** | ☐ Pending | Low |
| **Code** | ☐ Pending | Low |
| **Human** | ☐ Pending | Low |
| **Monitor** | ☐ Pending | Low |
| **Swarm** | ☐ Pending | Low |

## 🚀 **Next Steps**
1. Start with LLM operators (most commonly used)
2. Add factory registration methods to unified_registry.py
3. Update executors to use factory pattern
4. Add CLI scaffolds for new node types
5. Update documentation 