"""Document processing workflow using simple iceOS patterns."""

from typing import Dict, Any, List
from ice_orchestrator.workflow import Workflow
from ice_core.models.node_models import (
    ToolNodeConfig, 
    LLMOperatorConfig,
    CodeNodeConfig
)
from ice_core.models import LLMConfig, ModelProvider


def create_document_processing_workflow() -> Workflow:
    """Create document processing workflow using simple iceOS pattern."""
    
    # 1. TOOL NODE: Parse documents 
    document_parser = ToolNodeConfig(
        id="parse_documents",
        name="Extract text content from uploaded documents",
        type="tool",
        tool_name="document_parser",
        tool_args={
            "file_paths": "{{uploaded_files}}"
        }
    )
    
    # 2. TOOL NODE: Intelligent chunking
    chunking_tool = ToolNodeConfig(
        id="chunk_documents", 
        name="Create intelligent chunks",
        type="tool",
        tool_name="intelligent_chunker",
        dependencies=["parse_documents"],
        tool_args={
            "documents": "{{parse_documents.documents}}",
            "chunk_size": 1200,
            "overlap_size": 200,
            "strategy": "semantic"
        }
    )
    
    # 3. LLM NODE: Generate summary
    processing_summary = LLMOperatorConfig(
        id="generate_summary",
        name="Generate processing summary",
        type="llm",
        model="gpt-4o",
        dependencies=["chunk_documents"],
        prompt="""Documents processed successfully!

Documents: {{parse_documents.total_parsed}}
Chunks: {{chunk_documents.total_chunks}}

Generate a brief success message.""",
        llm_config=LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=200
        ),
        output_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Processing summary message"}
            },
            "required": ["summary"]
        }
    )
    
    # Create workflow
    nodes = [
        document_parser,
        chunking_tool, 
        processing_summary
    ]
    
    workflow = Workflow(
        nodes=nodes,
        name="document_processing",
        version="1.0.0"
    )
    
    return workflow


def create_simple_chat_workflow() -> Workflow:
    """Create FULLY FUNCTIONAL chat workflow with document search and LLM response."""
    
    # 1. TOOL NODE: Search documents for relevant chunks
    document_search = ToolNodeConfig(
        id="search_documents",
        name="Search documents for relevant information",
        type="tool",
        tool_name="semantic_search",
        tool_args={
            "query": "{{user_query}}",
            "document_collection": "{{document_collection}}",
            "limit": "{{max_results}}",
            "similarity_threshold": "{{similarity_threshold}}"
        }
    )
    
    # 2. LLM NODE: Generate contextual response
    chat_response = LLMOperatorConfig(
        id="chat_response",
        name="Generate contextual chat response",
        type="llm",
        model="gpt-4o",
        dependencies=["search_documents"],
        prompt="""You are a helpful assistant answering questions about uploaded documents.

User Question: {{user_query}}

Document Context:
{{#search_documents.results}}
- {{content}}
{{/search_documents.results}}

Based on the document context above, provide a comprehensive and helpful answer to the user's question. If the context doesn't contain enough information, say so clearly.

Guidelines:
- Use specific information from the documents when available
- Be concise but comprehensive
- If you can't find relevant information, explain what's missing
- Cite which documents contain the information when possible

Response:""",
        llm_config=LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=500
        ),
        output_schema={
            "type": "object",
            "properties": {
                "response": {"type": "string", "description": "Chat response text"},
                "confidence": {"type": "number", "description": "Response confidence 0-1"},
                "sources_used": {"type": "integer", "description": "Number of document sources used"}
            },
            "required": ["response", "confidence", "sources_used"]
        }
    )
    
    return Workflow(
        nodes=[document_search, chat_response],
        name="document_chat",
        version="1.0.0"
    ) 