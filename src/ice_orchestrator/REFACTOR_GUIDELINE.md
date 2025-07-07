# ice_orchestrator Refactor Guideline

## Current State Analysis

### Problems Identified

1. **Monolithic `script_chain.py`** (1047 lines)
   - Multiple responsibilities mixed together
   - Hard to navigate and maintain
   - Difficult to test individual components

2. **Flat file structure**
   - All files at root level
   - No logical grouping of related functionality
   - Inconsistent with CLI/SDK organization

3. **Mixed concerns**
   - Execution logic mixed with validation
   - Metrics mixed with core orchestration
   - Cache logic scattered throughout

4. **Deprecated shims**
   - `base_script_chain.py` and `workflow_execution_context.py` are just deprecation warnings
   - Creates confusion about where to import from

## Refactor Plan

### Phase 1: Create Directory Structure

```
src/ice_orchestrator/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── script_chain.py          # Main orchestration class (simplified)
│   └── chain_factory.py         # Factory methods for chain creation
├── execution/
│   ├── __init__.py
│   ├── executor.py              # Node execution logic
│   ├── retry_handler.py         # Retry logic
│   ├── metrics.py               # Metrics collection
│   └── cache_manager.py         # Cache management
├── graph/
│   ├── __init__.py
│   ├── dependency_graph.py      # Renamed from node_dependency_graph.py
│   └── level_resolver.py        # Level-based execution logic
├── validation/
│   ├── __init__.py
│   ├── chain_validator.py       # Chain validation logic
│   ├── schema_validator.py      # Output schema validation
│   └── security_validator.py    # Security and compliance checks
├── utils/
│   ├── __init__.py
│   ├── context_builder.py       # Context building utilities
│   ├── output_processor.py      # Output processing utilities
│   └── path_resolver.py         # Nested path resolution
├── errors/
│   ├── __init__.py
│   └── chain_errors.py          # Error classes
├── migration/
│   ├── __init__.py
│   └── chain_migrator.py        # Migration logic
└── docs/
    ├── API_GUIDE.md
    └── README.md
```

### Phase 2: Extract Components from script_chain.py

#### 2.1 Extract Execution Logic

**Current location**: `script_chain.py` lines 527-711
**New location**: `execution/executor.py`

```python
# execution/executor.py
class NodeExecutor:
    """Handles individual node execution with retry logic."""
    
    def __init__(self, context_manager, cache, failure_policy):
        self.context_manager = context_manager
        self.cache = cache
        self.failure_policy = failure_policy
    
    async def execute_node(self, node_id: str, input_data: Dict[str, Any]) -> NodeExecutionResult:
        # Extract the execute_node method logic here
        pass
    
    def _make_agent(self, node: AiNodeConfig) -> AgentNode:
        # Extract agent creation logic
        pass
```

#### 2.2 Extract Metrics Logic

**Current location**: `script_chain.py` lines 45-75
**New location**: `execution/metrics.py`

```python
# execution/metrics.py
class ChainMetrics(BaseModel):
    """Metrics for chain execution."""
    
    total_tokens: int = 0
    total_cost: float = 0.0
    node_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    def update(self, node_id: str, result: NodeExecutionResult) -> None:
        # Extract metrics update logic
        pass
```

#### 2.3 Extract Validation Logic

**Current location**: `script_chain.py` lines 771-845
**New location**: `validation/schema_validator.py`

```python
# validation/schema_validator.py
class SchemaValidator:
    """Validates node outputs against declared schemas."""
    
    @staticmethod
    def is_output_valid(node: NodeConfig, output: Any) -> bool:
        # Extract validation logic
        pass
```

#### 2.4 Extract Context Building

**Current location**: `script_chain.py` lines 400-442
**New location**: `utils/context_builder.py`

```python
# utils/context_builder.py
class ContextBuilder:
    """Builds execution context for nodes."""
    
    @staticmethod
    def build_node_context(
        node: NodeConfig,
        accumulated_results: Dict[str, NodeExecutionResult]
    ) -> Dict[str, Any]:
        # Extract context building logic
        pass
    
    @staticmethod
    def resolve_nested_path(data: Any, path: str) -> Any:
        # Extract path resolution logic
        pass
```

#### 2.5 Extract Branch Gating Logic

**Current location**: `script_chain.py` lines 846-903
**New location**: `graph/level_resolver.py`

```python
# graph/level_resolver.py
class BranchGatingResolver:
    """Handles conditional execution and branch gating."""
    
    def __init__(self, nodes, graph):
        self.nodes = nodes
        self.graph = graph
        self._branch_decisions: Dict[str, bool] = {}
        self._active_cache: Dict[str, bool] = {}
    
    def is_node_active(self, node_id: str) -> bool:
        # Extract branch gating logic
        pass
```

### Phase 3: Simplify Main ScriptChain Class

**Target**: Reduce `script_chain.py` from 1047 lines to ~300 lines

```python
# core/script_chain.py
class ScriptChain(BaseScriptChain):
    """Execute a directed acyclic workflow using level-based parallelism."""
    
    def __init__(self, nodes: List[NodeConfig], **kwargs):
        # Simplified initialization
        self.executor = NodeExecutor(...)
        self.metrics = ChainMetrics()
        self.validator = SchemaValidator()
        self.branch_resolver = BranchGatingResolver(nodes, self.graph)
        # ... other essential setup
    
    async def execute(self) -> ChainExecutionResult:
        # Simplified main execution loop
        # Delegate to specialized components
        pass
    
    async def _execute_level(self, level_nodes, accumulated_results):
        # Simplified level execution
        # Delegate to executor
        pass
```

### Phase 4: Update Imports and Dependencies

#### 4.1 Update Internal Imports

```python
# Before
from ice_orchestrator.chain_errors import ChainError
from ice_orchestrator.node_dependency_graph import DependencyGraph

# After
from ice_orchestrator.errors.chain_errors import ChainError
from ice_orchestrator.graph.dependency_graph import DependencyGraph
```

#### 4.2 Update External Imports

Update all files that import from `ice_orchestrator` to use the new structure.

### Phase 5: Remove Deprecated Shim Files

1. **Remove**: `base_script_chain.py` (deprecated shim)
2. **Remove**: `workflow_execution_context.py` (deprecated shim)
3. **Update**: All imports to use `ice_sdk.orchestrator.*` directly

### Phase 6: Add Comprehensive Tests

Create tests for each extracted component:

```python
# tests/orchestrator/test_execution.py
class TestNodeExecutor:
    async def test_execute_node_success(self):
        pass
    
    async def test_execute_node_retry(self):
        pass

# tests/orchestrator/test_validation.py
class TestSchemaValidator:
    def test_output_validation_success(self):
        pass
    
    def test_output_validation_failure(self):
        pass
```

## Implementation Guidelines

### 1. Preserve Public API

- All public methods must maintain the same signatures
- Use deprecation warnings for any breaking changes
- Maintain backward compatibility during transition

### 2. Follow iceOS Patterns

- Use type hints and Pydantic models
- Follow async/await patterns
- Use structured logging with structlog
- Implement proper error handling

### 3. Maintain Layer Boundaries

- Don't import from `app.*` inside `ice_orchestrator.*`
- Keep external side-effects in Tool implementations
- Follow the established dependency direction

### 4. Code Quality Standards

- Use type hints everywhere
- Add comprehensive docstrings
- Follow the existing code style
- Add proper error handling

### 5. Testing Strategy

- Test each extracted component in isolation
- Maintain existing integration tests
- Add new unit tests for extracted logic
- Ensure test coverage doesn't decrease

## Migration Checklist

- [ ] Create new directory structure
- [ ] Extract execution logic to `execution/executor.py`
- [ ] Extract metrics logic to `execution/metrics.py`
- [ ] Extract validation logic to `validation/schema_validator.py`
- [ ] Extract context building to `utils/context_builder.py`
- [ ] Extract branch gating to `graph/level_resolver.py`
- [ ] Simplify main ScriptChain class
- [ ] Update all imports throughout codebase
- [ ] Remove deprecated shim files
- [ ] Add comprehensive tests
- [ ] Update documentation
- [ ] Run full test suite
- [ ] Update CI/CD if needed

## Benefits After Refactor

1. **Maintainability**: Smaller, focused modules
2. **Testability**: Each component can be tested in isolation
3. **Readability**: Clear separation of concerns
4. **Consistency**: Matches CLI/SDK organization patterns
5. **Extensibility**: Easy to add new features to specific components
6. **Debugging**: Easier to trace issues to specific components

## Risk Mitigation

1. **Incremental Migration**: Extract one component at a time
2. **Comprehensive Testing**: Ensure no regressions
3. **Backward Compatibility**: Maintain existing APIs
4. **Documentation**: Update all references
5. **Rollback Plan**: Keep old structure until new one is proven 