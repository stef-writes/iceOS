"""Semantic memory for storing facts and domain knowledge."""

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMemory, MemoryConfig, MemoryEntry


class SemanticMemory(BaseMemory):
    """Memory for storing facts and domain knowledge.
    
    Supports vector search when enable_vector_search is True.
    Can be extended with Supabase/pgvector for production use.
    
    Use cases:
    - Product specifications and details
    - Pricing rules and policies
    - Domain facts and relationships
    - Learned insights and patterns
    """
    
    def __init__(self, config: MemoryConfig):
        """Initialize semantic memory."""
        super().__init__(config)
        self._facts_store: Dict[str, MemoryEntry] = {}
        self._embeddings: Dict[str, List[float]] = {}
        
        # 🚀 NESTED STRUCTURE: Much better performance!
        self._relationships: Dict[str, Dict[str, List[Tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
        self._entity_index: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        
        self._embedding_dim = 384  # Default dimension for embeddings
        self._enable_vectors = config.enable_vector_search
        
    async def initialize(self) -> None:
        """Initialize semantic memory backend."""
        if self._initialized:
            return
            
        # In production, would connect to vector store here
        # For now, using in-memory implementation
        self._initialized = True
    
    # 🚀 NEW: High-performance nested query methods
    def get_entities_by_domain(self, domain: str) -> List[str]:
        """Get all entities in a specific domain - MUCH faster than iterating all!"""
        return list(self._entity_index.get(domain, {}).keys())
    
    def get_facts_for_entity_in_domain(self, entity: str, domain: str) -> List[str]:
        """Get fact keys for entity in specific domain - targeted querying!"""
        return self._entity_index.get(domain, {}).get(entity, [])
    
    def get_relationships_by_type(self, rel_type: str) -> Dict[str, List[Tuple[str, float]]]:
        """Get all relationships of a specific type - organized access!"""
        relationships = self._relationships.get(rel_type, {})
        return {k: [(target, float(strength)) for target, strength in v] for k, v in relationships.items()}
    
    def list_domains(self) -> List[str]:
        """List all domains with entities - great for analytics!"""
        return list(self._entity_index.keys())
    
    def list_relationship_types(self) -> List[str]:
        """List all relationship types - perfect for exploration!"""
        return list(self._relationships.keys())
        
    async def store(
        self,
        key: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a fact or piece of knowledge."""
        if not self._initialized:
            await self.initialize()
            
        metadata = metadata or {}
        
        # Create memory entry
        entry = MemoryEntry(
            key=key,
            content=content,
            metadata=metadata,
            timestamp=datetime.now()
        )
        
        # Add semantic-specific metadata
        entry.metadata.update({
            "fact_type": metadata.get("type", "general"),
            "entities": metadata.get("entities", []),
            "domain": metadata.get("domain", "general"),
            "confidence": metadata.get("confidence", 1.0),
            "source": metadata.get("source", "system"),
            "relationships": metadata.get("relationships", [])
        })
        
        # Store the fact
        self._facts_store[key] = entry
        
        # Index entities by domain for much better query performance
        domain = entry.metadata.get("domain", "general")
        for entity in entry.metadata.get("entities", []):
            self._entity_index[domain][entity].append(key)
            
        # Store relationships by relationship type for better querying  
        for rel in entry.metadata.get("relationships", []):
            if isinstance(rel, dict) and "target" in rel and "type" in rel:
                rel_type = rel["type"]
                self._relationships[rel_type][key].append((rel["target"], rel.get("strength", 1.0)))
                
        # Generate and store embedding if vector search is enabled
        if self._enable_vectors:
            embedding = await self._generate_embedding(content)
            self._embeddings[key] = embedding
            
    async def _generate_embedding(self, content: Any) -> List[float]:
        """Generate embedding for content."""
        # Simple hash-based embedding for demonstration
        # In production, would use actual embedding model
        content_str = json.dumps(content) if not isinstance(content, str) else content
        hash_obj = hashlib.sha384(content_str.encode())
        hash_bytes = hash_obj.digest()
        vector = [byte / 255.0 for byte in hash_bytes[: self._embedding_dim]]
        norm = (sum(x * x for x in vector) ** 0.5) or 1.0
        return [x / norm for x in vector]
        
    async def retrieve(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve a specific fact."""
        if not self._initialized:
            await self.initialize()
            
        return self._facts_store.get(key)
        
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search facts semantically."""
        if not self._initialized:
            await self.initialize()
            
        filters = filters or {}
        
        if self._enable_vectors and query:
            # Vector similarity search
            query_embedding = await self._generate_embedding(query)
            results = await self._vector_search(query_embedding, limit * 2, filters)
        else:
            # Fallback to text search
            results = []
            for key, entry in self._facts_store.items():
                # Apply filters
                if not self._match_filters(entry, filters):
                    continue
                    
                # Simple text matching
                content_str = str(entry.content).lower()
                if query.lower() in content_str:
                    results.append(entry)
                    
        # Sort by relevance/timestamp
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        return results[:limit]
        
    async def _vector_search(
        self,
        query_embedding: List[float],
        limit: int,
        filters: Dict[str, Any]
    ) -> List[MemoryEntry]:
        """Perform vector similarity search."""
        similarities = []
        
        for key, embedding in self._embeddings.items():
            entry = self._facts_store.get(key)
            if not entry or not self._match_filters(entry, filters):
                continue
                
            # Cosine similarity (dot product since vectors are normalized)
            similarity = sum(q * e for q, e in zip(query_embedding, embedding))
            similarities.append((similarity, entry))
            
        # Sort by similarity
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        return [entry for _, entry in similarities[:limit]]
        
    def _match_filters(self, entry: MemoryEntry, filters: Dict[str, Any]) -> bool:
        """Check if entry matches filters."""
        if not filters:
            return True
            
        metadata = entry.metadata
        
        if "type" in filters and metadata.get("fact_type") != filters["type"]:
            return False
            
        if "domain" in filters and metadata.get("domain") != filters["domain"]:
            return False
            
        if "entities" in filters:
            entry_entities = set(metadata.get("entities", []))
            filter_entities = set(filters["entities"])
            if not filter_entities.intersection(entry_entities):
                return False
                
        if "min_confidence" in filters:
            if metadata.get("confidence", 0) < filters["min_confidence"]:
                return False
                
        return True
        
    async def delete(self, key: str) -> bool:
        """Delete a fact."""
        if not self._initialized:
            await self.initialize()
            
        if key not in self._facts_store:
            return False
            
        entry = self._facts_store[key]
        
        # Remove from nested entity index
        domain = entry.metadata.get("domain", "general")
        for entity in entry.metadata.get("entities", []):
            if domain in self._entity_index and entity in self._entity_index[domain]:
                self._entity_index[domain][entity].remove(key)
                if not self._entity_index[domain][entity]:
                    del self._entity_index[domain][entity]
                    if not self._entity_index[domain]:
                        del self._entity_index[domain]
                    
        # Remove from nested relationships
        for rel in entry.metadata.get("relationships", []):
            if isinstance(rel, dict) and "type" in rel:
                rel_type = rel["type"]
                if rel_type in self._relationships and key in self._relationships[rel_type]:
                    del self._relationships[rel_type][key]
                    if not self._relationships[rel_type]:
                        del self._relationships[rel_type]
            
        # Remove embedding
        if key in self._embeddings:
            del self._embeddings[key]
            
        # Remove fact
        del self._facts_store[key]
        
        return True
        
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear facts matching pattern."""
        if not self._initialized:
            await self.initialize()
            
        if pattern:
            keys_to_delete = [k for k in self._facts_store.keys() if k.startswith(pattern)]
        else:
            keys_to_delete = list(self._facts_store.keys())
            
        count = 0
        for key in keys_to_delete:
            if await self.delete(key):
                count += 1
                
        return count
        
    async def list_keys(
        self,
        pattern: Optional[str] = None,
        limit: int = 100
    ) -> List[str]:
        """List fact keys."""
        if not self._initialized:
            await self.initialize()
            
        if pattern:
            keys = [k for k in self._facts_store.keys() if k.startswith(pattern)]
        else:
            keys = list(self._facts_store.keys())
            
        return keys[:limit]
        
    async def find_related(
        self,
        entity: str,
        relationship_type: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Find facts related to an entity."""
        if not self._initialized:
            await self.initialize()
            
        # Find facts containing this entity
        entity_data = self._entity_index.get(entity, {})
        fact_keys: List[str] = []
        for domain_entities in entity_data.values():
            fact_keys.extend(domain_entities)
        
        related_facts = []
        for key in fact_keys:
            entry = self._facts_store.get(key)
            if entry:
                # Check relationship type if specified
                if relationship_type:
                    relationships_data: Any = self._relationships.get(key, [])
                    if isinstance(relationships_data, list):
                        relationships: List[Tuple[str, float]] = []
                        for rel_data in relationships_data:
                            if isinstance(rel_data, (list, tuple)) and len(rel_data) >= 2:
                                relationships.append((str(rel_data[0]), float(rel_data[1])))
                        if any(rel[0] == relationship_type for rel in relationships):
                            related_facts.append(entry)
                else:
                    related_facts.append(entry)
                    
        return related_facts[:limit]
        
    async def get_knowledge_graph(
        self,
        root_entity: str,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """Build a knowledge graph starting from an entity."""
        if not self._initialized:
            await self.initialize()
            
        graph: Dict[str, Any] = {
            "nodes": {},
            "edges": []
        }
        
        visited = set()
        queue = [(root_entity, 0)]
        
        while queue:
            entity, depth = queue.pop(0)
            
            if entity in visited or depth > max_depth:
                continue
                
            visited.add(entity)
            
            # Add node
            graph["nodes"][entity] = {
                "type": "entity",
                "depth": depth,
                "facts": []
            }
            
            # Find facts about this entity across all domains
            fact_keys = []
            for domain_entities in self._entity_index.values():
                fact_keys.extend(domain_entities.get(entity, []))
            for key in fact_keys[:5]:  # Limit facts per entity
                entry = self._facts_store.get(key)
                if entry:
                    graph["nodes"][entity]["facts"].append({
                        "key": key,
                        "content": str(entry.content)[:100],
                        "type": entry.metadata.get("fact_type", "general")
                    })
                    
                    # Add relationships
                    relationships_data: Any = self._relationships.get(key, [])
                    if isinstance(relationships_data, list):
                        relationships: List[Tuple[str, float]] = []
                        for rel_data in relationships_data:
                            if isinstance(rel_data, (list, tuple)) and len(rel_data) >= 2:
                                relationships.append((str(rel_data[0]), float(rel_data[1])))
                        for rel_data in relationships:
                            if isinstance(rel_data, (list, tuple)) and len(rel_data) >= 2:
                                rel_type, target_raw = rel_data[0], rel_data[1]
                                target: str = str(target_raw)
                                graph["edges"].append({
                                    "source": entity,
                                    "target": target,
                                    "type": rel_type
                                })
                                # Add to queue for traversal if we have not exceeded max depth
                                if depth < max_depth:
                                    queue.append((target, depth + 1))
                            
        return graph
        
    async def learn_from_interaction(
        self,
        interaction_data: Dict[str, Any]
    ) -> List[str]:
        """Learn new facts from an interaction."""
        # Extract facts from interaction
        facts_learned = []
        
        # Example: Learn pricing patterns
        if "sale_price" in interaction_data and "item_condition" in interaction_data:
            fact_key = f"pricing_pattern_{interaction_data['item_type']}_{interaction_data['item_condition']}"
            await self.store(
                key=fact_key,
                content={
                    "pattern": "typical_price",
                    "item_type": interaction_data["item_type"],
                    "condition": interaction_data["item_condition"],
                    "price_range": interaction_data["sale_price"]
                },
                metadata={
                    "type": "pricing_pattern",
                    "entities": [interaction_data["item_type"], interaction_data["item_condition"]],
                    "domain": "marketplace",
                    "confidence": 0.8,
                    "source": "learned"
                }
            )
            facts_learned.append(fact_key)
            
        # Learn customer preferences
        if "customer_id" in interaction_data and "preferences" in interaction_data:
            pref_key = f"customer_pref_{interaction_data['customer_id']}"
            await self.store(
                key=pref_key,
                content=interaction_data["preferences"],
                metadata={
                    "type": "customer_preference",
                    "entities": [interaction_data["customer_id"]],
                    "domain": "customers",
                    "confidence": 0.9
                }
            )
            facts_learned.append(pref_key)
            
        return facts_learned
        
    async def get_domain_knowledge(
        self,
        domain: str,
        fact_type: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Get all knowledge in a specific domain."""
        filters = {"domain": domain}
        if fact_type:
            filters["type"] = fact_type
            
        return await self.search("", filters=filters, limit=100)
        
    async def merge_facts(
        self,
        keys: List[str],
        merged_key: str
    ) -> bool:
        """Merge multiple facts into one."""
        if not self._initialized:
            await self.initialize()
            
        facts_to_merge = []
        all_entities = set()
        all_relationships = []
        
        for key in keys:
            entry = self._facts_store.get(key)
            if entry:
                facts_to_merge.append(entry)
                all_entities.update(entry.metadata.get("entities", []))
                all_relationships.extend(entry.metadata.get("relationships", []))
                
        if not facts_to_merge:
            return False
            
        # Create merged content
        merged_content = {
            "merged_from": keys,
            "facts": [f.content for f in facts_to_merge],
            "merged_at": datetime.now().isoformat()
        }
        
        # Store merged fact
        await self.store(
            key=merged_key,
            content=merged_content,
            metadata={
                "type": "merged_fact",
                "entities": list(all_entities),
                "relationships": all_relationships,
                "source": "merge_operation"
            }
        )
        
        # Delete original facts
        for key in keys:
            await self.delete(key)
            
        return True 