"""Intelligent document chunker for optimal text segmentation."""

import re
from typing import Dict, Any, List
from ice_sdk.tools.base import ToolBase


class IntelligentChunkerTool(ToolBase):
    """Smart document segmentation that preserves semantic meaning.
    
    This tool is highly reusable for any workflow requiring intelligent
    text chunking for RAG, summarization, or other NLP tasks.
    """
    
    name: str = "intelligent_chunker"
    description: str = "Smart document segmentation preserving semantic boundaries"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(
        self,
        documents: List[Dict[str, Any]] = None,
        chunk_size: int = 1000,
        overlap_size: int = 200,
        strategy: str = "semantic",
        **kwargs
    ) -> Dict[str, Any]:
        """Intelligently chunk documents into optimally-sized segments."""
        
        if not documents:
            return {
                "success": False,
                "error": "No documents provided for chunking",
                "chunks": []
            }
        
        print(f"🧩 Chunking {len(documents)} document(s) using {strategy} strategy")
        print(f"📏 Chunk size: {chunk_size} chars, Overlap: {overlap_size} chars")
        
        all_chunks = []
        processing_stats = {
            "total_documents": len(documents),
            "total_chunks": 0,
            "avg_chunks_per_doc": 0,
            "strategy_used": strategy
        }
        
        for doc_idx, document in enumerate(documents):
            try:
                doc_chunks = await self._chunk_single_document(
                    document=document,
                    chunk_size=chunk_size,
                    overlap_size=overlap_size,
                    strategy=strategy,
                    doc_index=doc_idx
                )
                all_chunks.extend(doc_chunks)
                print(f"✂️  Document {doc_idx + 1}: {len(doc_chunks)} chunks created")
                
            except Exception as e:
                print(f"❌ Failed to chunk document {doc_idx + 1}: {e}")
                continue
        
        processing_stats["total_chunks"] = len(all_chunks)
        processing_stats["avg_chunks_per_doc"] = len(all_chunks) / max(len(documents), 1)
        
        return {
            "success": True,
            "chunks": all_chunks,
            "processing_stats": processing_stats
        }
    
    async def _chunk_single_document(
        self,
        document: Dict[str, Any],
        chunk_size: int,
        overlap_size: int,
        strategy: str,
        doc_index: int
    ) -> List[Dict[str, Any]]:
        """Chunk a single document using the specified strategy."""
        
        content = document.get("content", "")
        metadata = document.get("metadata", {})
        
        if strategy == "semantic":
            chunks = self._semantic_chunking(content, chunk_size, overlap_size)
        elif strategy == "sentence":
            chunks = self._sentence_chunking(content, chunk_size, overlap_size)
        elif strategy == "paragraph":
            chunks = self._paragraph_chunking(content, chunk_size, overlap_size)
        else:  # "fixed"
            chunks = self._fixed_chunking(content, chunk_size, overlap_size)
        
        # Add metadata to each chunk
        enriched_chunks = []
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_data = {
                "content": chunk_text,
                "chunk_id": f"doc_{doc_index}_chunk_{chunk_idx}",
                "chunk_index": chunk_idx,
                "document_index": doc_index,
                "source_metadata": metadata,
                "char_count": len(chunk_text),
                "word_count": len(chunk_text.split()),
                "strategy": strategy
            }
            enriched_chunks.append(chunk_data)
        
        return enriched_chunks
    
    def _semantic_chunking(self, content: str, chunk_size: int, overlap_size: int) -> List[str]:
        """Semantic chunking that respects topic boundaries."""
        
        # Split by natural semantic boundaries (paragraphs, sections)
        sections = self._identify_sections(content)
        chunks = []
        current_chunk = ""
        
        for section in sections:
            # If adding this section would exceed chunk size, finalize current chunk
            if current_chunk and len(current_chunk) + len(section) > chunk_size:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, overlap_size)
                current_chunk = overlap_text + section
            else:
                current_chunk += "\n\n" + section if current_chunk else section
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _sentence_chunking(self, content: str, chunk_size: int, overlap_size: int) -> List[str]:
        """Sentence-aware chunking that doesn't break sentences."""
        
        sentences = self._split_into_sentences(content)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size, finalize current chunk
            if current_chunk and len(current_chunk) + len(sentence) > chunk_size:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, overlap_size)
                current_chunk = overlap_text + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _paragraph_chunking(self, content: str, chunk_size: int, overlap_size: int) -> List[str]:
        """Paragraph-based chunking."""
        
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if current_chunk and len(current_chunk) + len(paragraph) > chunk_size:
                chunks.append(current_chunk.strip())
                
                overlap_text = self._get_overlap_text(current_chunk, overlap_size)
                current_chunk = overlap_text + paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _fixed_chunking(self, content: str, chunk_size: int, overlap_size: int) -> List[str]:
        """Simple fixed-size chunking with overlap."""
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            
            # Try to end at word boundary
            if end < len(content):
                last_space = chunk.rfind(' ')
                if last_space > chunk_size * 0.8:  # If space is reasonably close to end
                    chunk = chunk[:last_space]
                    end = start + last_space
            
            chunks.append(chunk.strip())
            start = end - overlap_size
            
            if start >= len(content):
                break
        
        return [chunk for chunk in chunks if chunk.strip()]
    
    def _identify_sections(self, content: str) -> List[str]:
        """Identify natural sections in the document."""
        
        # Look for headers, numbered sections, etc.
        section_patterns = [
            r'^#{1,6}\s+.+$',  # Markdown headers
            r'^\d+\.\s+.+$',   # Numbered sections
            r'^[A-Z][A-Z\s]+:',  # ALL CAPS headers
            r'^\[.*\]$'        # [Section] headers
        ]
        
        lines = content.split('\n')
        sections = []
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line is a section header
            is_header = any(re.match(pattern, line, re.MULTILINE) for pattern in section_patterns)
            
            if is_header and current_section:
                # Finalize current section
                sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        # Add final section
        if current_section:
            sections.append('\n'.join(current_section))
        
        # If no sections found, split by paragraphs
        if len(sections) <= 1:
            sections = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        return sections
    
    def _split_into_sentences(self, content: str) -> List[str]:
        """Split content into sentences using regex."""
        
        # Basic sentence splitting (can be enhanced with spaCy/NLTK)
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, content)
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from the end of previous chunk."""
        
        if len(text) <= overlap_size:
            return text + " "
        
        # Try to get overlap at word boundary
        overlap = text[-overlap_size:]
        first_space = overlap.find(' ')
        
        if first_space > 0:
            overlap = overlap[first_space:]
        
        return overlap + " "
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "metadata": {"type": "object"}
                        },
                        "required": ["content"]
                    },
                    "description": "List of documents to chunk"
                },
                "chunk_size": {
                    "type": "integer",
                    "default": 1000,
                    "description": "Target size for each chunk in characters"
                },
                "overlap_size": {
                    "type": "integer", 
                    "default": 200,
                    "description": "Overlap between chunks in characters"
                },
                "strategy": {
                    "type": "string",
                    "enum": ["semantic", "sentence", "paragraph", "fixed"],
                    "default": "semantic",
                    "description": "Chunking strategy to use"
                }
            },
            "required": ["documents"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return output schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "chunks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "chunk_id": {"type": "string"},
                            "chunk_index": {"type": "integer"},
                            "document_index": {"type": "integer"},
                            "source_metadata": {"type": "object"},
                            "char_count": {"type": "integer"},
                            "word_count": {"type": "integer"},
                            "strategy": {"type": "string"}
                        }
                    }
                },
                "processing_stats": {"type": "object"}
            },
            "required": ["success", "chunks"]
        } 