# 🧠 iceOS Memory System Architecture

## Architecture Overview

The iceOS memory subsystem resides in the **core layer** (`ice_core.memory`) and currently ships four complementary stores:

- WorkingMemory – short-term, in-process context (optionally Redis-backed)
- EpisodicMemory – conversation history
- SemanticMemory – domain knowledge with entity & relationship indexing
- ProceduralMemory – reusable action patterns and success metrics

## 📋 **Memory Types**

### 🔍 **Semantic Memory**
Stores facts, entities, and relationships with domain-based organization.

**Enhanced Structure:**
```python
# OLD (flat): Dict[str, List[...]]
_entity_index: Dict[str, List[str]]  # "entity" -> [fact_keys]

# NEW (nested): Dict[domain, Dict[entity, List[...]]]
_entity_index: Dict[str, Dict[str, List[str]]]  # domain -> entity -> [fact_keys]
```



### 🛠️ **Procedural Memory**
Stores procedures, success metrics, and usage patterns by category and domain.

**Enhanced Structure:**
```python
# OLD (flat): Dict[str, List[...]]
_category_index: Dict[str, List[str]]  # "category" -> [procedure_keys]

# NEW (nested): Dict[category, Dict[type, List[...]]]
_category_index: Dict[str, Dict[str, List[str]]]  # category -> type -> [procedure_keys]
```



## 🎯 **Usage Examples**

### Simplified Configuration
```python
# OLD: Complex nested configuration
config = UnifiedMemoryConfig(
    working_config=MemoryConfig(backend="memory"),
    episodic_config=MemoryConfig(backend="redis"),
    semantic_config=MemoryConfig(backend="sqlite"),
    procedural_config=MemoryConfig(backend="file")
)

# NEW: Simple configuration with smart defaults
config = UnifiedMemoryConfig(
    backend="redis",
    enable_vector_search=True,
    domains=["marketplace", "pricing", "inventory"]
)
```

### Dependency Injection
```python
# Create memory instance
memory = UnifiedMemory(UnifiedMemoryConfig())

# Inject into agent
agent = MemoryAgent(config, memory=memory)
```

### Analytics Capabilities
```python
# Get usage statistics
stats = await memory.get_usage_stats()

# Get domain analytics
analytics = await memory.get_domain_analytics()

# Get performance metrics
metrics = await memory.get_performance_metrics()
```

### High-Performance Queries
```python
# Get all marketplace entities (O(1) instead of O(n))
entities = semantic_memory.get_entities_by_domain('marketplace')

# Get negotiation procedures of specific type (O(1))
procedures = procedural_memory.get_procedures_by_category('negotiation', 'price_strategy')

# Get all relationship types for analytics (O(1))
rel_types = semantic_memory.list_relationship_types()
```

### Analytics & Monitoring
```python
# Domain-based analytics
for domain in semantic_memory.list_domains():
    entity_count = len(semantic_memory.get_entities_by_domain(domain))
    print(f"{domain}: {entity_count} entities")

# Performance monitoring
for domain in procedural_memory.list_domains():
    metrics = procedural_memory.get_success_metrics_for_domain(domain)
    usage = procedural_memory.get_usage_stats_for_domain(domain)
    print(f"{domain}: {len(metrics)} procedures, {sum(usage.values())} total uses")
```

## 🔧 **Migration Notes**

**✅ Backward Compatible API:** All existing `store()`, `retrieve()`, `search()` methods work unchanged.

**🚀 New Methods Available:**
- `get_entities_by_domain(domain)` - Targeted entity queries
- `get_relationships_by_type(rel_type)` - Organized relationship access
- `get_procedures_by_category(category, type)` - Structured procedure lookup
- `list_domains()`, `list_relationship_types()`, `list_categories()` - Analytics



## 🎭 **Real-World Usage**

This architecture powers our **Facebook Marketplace demo** with:
- **Domain separation:** `marketplace`, `pricing`, `inventory`, `customer_service`
- **Fast entity lookup:** Get all marketplace products in milliseconds
- **Relationship queries:** Find pricing strategies by type instantly
- **Performance monitoring:** Track success rates by domain
