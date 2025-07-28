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
        )
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
    """Simple chat workflow stub."""
    
    # Simple chat response
    chat_response = LLMOperatorConfig(
        id="chat_response",
        name="Generate chat response",
        type="llm",
        model="gpt-4o",
        prompt="User question: {{user_question}}\n\nProvide a helpful response.",
        llm_config=LLMConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=300
        )
    )
    
    return Workflow(
        nodes=[chat_response],
        name="document_chat",
        version="1.0.0"
    ) 