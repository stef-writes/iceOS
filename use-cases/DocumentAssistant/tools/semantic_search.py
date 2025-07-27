"""Semantic search tool for document retrieval."""

from typing import Dict, Any, List
from ice_sdk.tools.base import ToolBase


class SemanticSearchTool(ToolBase):
    """Search document chunks using semantic similarity.
    
    Reusable tool for any workflow requiring document retrieval
    based on semantic similarity and metadata filtering.
    """
    
    name: str = "semantic_search"
    description: str = "Search document chunks using semantic similarity"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(
        self,
        query: str,
        document_collection: str = "default",
        limit: int = 5,
        similarity_threshold: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for semantically similar document chunks."""
        
        if not query.strip():
            return {
                "success": False,
                "error": "No search query provided",
                "results": []
            }
        
        print(f"🔍 Searching for: '{query}' in collection '{document_collection}'")
        print(f"📊 Limit: {limit}, Threshold: {similarity_threshold}")
        
        # Simulate semantic search results
        # In real implementation, would use vector database
        search_results = self._simulate_semantic_search(
            query=query,
            collection=document_collection,
            limit=limit,
            threshold=similarity_threshold
        )
        
        print(f"✅ Found {len(search_results)} relevant chunks")
        
        return {
            "success": True,
            "results": search_results,
            "query": query,
            "total_results": len(search_results),
            "collection": document_collection
        }
    
    def _simulate_semantic_search(
        self,
        query: str,
        collection: str,
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Simulate semantic search with realistic results."""
        
        # Simulate document chunks with relevance scores
        simulated_chunks = [
            {
                "chunk_id": "doc_0_chunk_0",
                "content": f"This is a relevant section about {query.lower()}. It contains detailed information that directly answers the user's question about the topic.",
                "similarity_score": 0.95,
                "metadata": {
                    "source_file": "document1.pdf",
                    "chunk_index": 0,
                    "word_count": 24,
                    "document_collection": collection
                }
            },
            {
                "chunk_id": "doc_0_chunk_3", 
                "content": f"Additional context related to {query.lower()}. This section provides supporting information and examples that complement the main discussion.",
                "similarity_score": 0.88,
                "metadata": {
                    "source_file": "document1.pdf",
                    "chunk_index": 3,
                    "word_count": 21,
                    "document_collection": collection
                }
            },
            {
                "chunk_id": "doc_1_chunk_1",
                "content": f"Background information about {query.lower()}. This provides foundational knowledge that helps understand the broader context of the topic.",
                "similarity_score": 0.82,
                "metadata": {
                    "source_file": "document2.txt",
                    "chunk_index": 1,
                    "word_count": 19,
                    "document_collection": collection
                }
            },
            {
                "chunk_id": "doc_0_chunk_7",
                "content": f"A brief mention of {query.lower()} appears in this section, along with other topics that may be tangentially related to the user's inquiry.",
                "similarity_score": 0.75,
                "metadata": {
                    "source_file": "document1.pdf", 
                    "chunk_index": 7,
                    "word_count": 23,
                    "document_collection": collection
                }
            },
            {
                "chunk_id": "doc_2_chunk_0",
                "content": f"Some peripheral information that touches on aspects of {query.lower()}, though not directly addressing the main question.",
                "similarity_score": 0.71,
                "metadata": {
                    "source_file": "document3.docx",
                    "chunk_index": 0,
                    "word_count": 18,
                    "document_collection": collection
                }
            }
        ]
        
        # Filter by similarity threshold
        relevant_chunks = [
            chunk for chunk in simulated_chunks 
            if chunk["similarity_score"] >= threshold
        ]
        
        # Sort by similarity score and limit results
        relevant_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
        return relevant_chunks[:limit]
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text"
                },
                "document_collection": {
                    "type": "string",
                    "default": "default",
                    "description": "Document collection to search"
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of results to return"
                },
                "similarity_threshold": {
                    "type": "number",
                    "default": 0.7,
                    "description": "Minimum similarity score for results"
                }
            },
            "required": ["query"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return output schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chunk_id": {"type": "string"},
                            "content": {"type": "string"},
                            "similarity_score": {"type": "number"},
                            "metadata": {"type": "object"}
                        }
                    }
                },
                "query": {"type": "string"},
                "total_results": {"type": "integer"},
                "collection": {"type": "string"}
            },
            "required": ["success", "results"]
        } 