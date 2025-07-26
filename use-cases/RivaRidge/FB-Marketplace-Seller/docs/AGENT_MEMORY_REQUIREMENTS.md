# Agent Memory Requirements for Basic Functionality

## Current State in iceOS

### ✅ What EXISTS:
1. **Session State** - Conversation history within a session
2. **Context Store** - Node outputs and intermediate results  
3. **GraphContextManager** - Manages context flow between nodes
4. **BaseMemory Interface** - Protocol for memory implementations
5. **Redis** - For caching and real-time state

### ❌ What's MISSING for Basic Agents:

## 1. Short-Term Memory (Working Memory)
**What**: Temporary storage during agent reasoning cycles
**Why**: Agents need to track their current thought process
**Implementation**: Simple in-memory dictionary with TTL

```python
class WorkingMemory:
    def __init__(self, ttl_seconds: int = 300):
        self._memory: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        
    def set(self, key: str, value: Any):
        self._memory[key] = value
        self._timestamps[key] = datetime.now()
        
    def get(self, key: str) -> Any:
        # Check TTL and return value
        pass
```

## 2. Episodic Memory (Conversation Memory)
**What**: Past conversations and interactions
**Why**: Remember customer preferences, past issues
**Implementation**: Redis with structured format

```python
class EpisodicMemory:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def add_interaction(self, user_id: str, interaction: Dict):
        key = f"episode:{user_id}:{datetime.now().isoformat()}"
        await self.redis.set(key, json.dumps(interaction))
        
    async def get_recent_interactions(self, user_id: str, limit: int = 10):
        # Retrieve recent interactions for context
        pass
```

## 3. Semantic Memory (Facts Storage) 
**What**: Domain facts and learned information
**Why**: Remember product details, pricing rules, policies
**Implementation**: Key-value store with optional vector search

```python
class SemanticMemory:
    def __init__(self, storage_backend):
        self.storage = storage_backend
        
    async def store_fact(self, category: str, fact: str, metadata: Dict):
        # Store categorized facts
        pass
        
    async def recall_facts(self, category: str, query: str) -> List[str]:
        # Retrieve relevant facts
        pass
```

## 4. Procedural Memory (Action Templates)
**What**: Successful action sequences and patterns
**Why**: Reuse successful strategies
**Implementation**: JSON templates in Redis/File

```python
class ProceduralMemory:
    def __init__(self):
        self.procedures = {}
        
    def store_procedure(self, name: str, steps: List[Dict]):
        self.procedures[name] = {
            "steps": steps,
            "success_rate": 0.0,
            "last_used": datetime.now()
        }
```

## What to Add to ice_sdk

### 1. Create `ice_sdk/memory/` module:
```
ice_sdk/memory/
├── __init__.py
├── base.py          # Enhanced base classes
├── working.py       # Working memory implementation
├── episodic.py      # Conversation memory
├── semantic.py      # Facts storage
├── procedural.py    # Action patterns
└── unified.py       # Unified memory interface
```

### 2. Enhance AgentNode base class:
```python
class EnhancedAgentNode(AgentNode):
    def __init__(self, memory_config: Dict[str, Any] = None):
        super().__init__()
        self.memory = UnifiedMemory(memory_config or {
            "working": {"ttl": 300},
            "episodic": {"backend": "redis"},
            "semantic": {"backend": "sqlite"},
            "procedural": {"backend": "file"}
        })
```

## For Your FB Marketplace Use Case

### Minimum Viable Memory:
1. **Working Memory** - Track current negotiation state
2. **Episodic Memory** - Remember customer conversations
3. **Semantic Memory** - Store product facts and pricing

### Implementation Priority:
1. Start with in-memory + Redis
2. Add SQLite for persistence
3. Upgrade to vector search later

## NO Knowledge Graphs Needed (Yet!)

Knowledge graphs are overkill for basic agent functionality. You need them when:
- Complex relationship reasoning is required
- Multi-hop inference is needed
- Domain ontology becomes complex

For now, simple key-value and vector storage will handle 95% of agent needs! 