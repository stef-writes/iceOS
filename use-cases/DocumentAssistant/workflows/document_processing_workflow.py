"""Document processing workflow showcasing iceOS orchestration capabilities."""

from typing import Dict, Any, List
from ice_core.models.workflow import WorkflowConfig
from ice_core.models.node_models import (
    ToolNodeConfig, 
    LLMOperatorConfig,
    CodeNodeConfig,
    ConditionNodeConfig,
    LoopNodeConfig
)
from ice_core.models.llm import LLMConfig, ModelProvider


class DocumentProcessingWorkflow:
    """Sophisticated workflow demonstrating iceOS's orchestration capabilities.
    
    This workflow showcases:
    - Conditional nodes: Check document validity and processing requirements
    - Loop nodes: Process multiple documents efficiently 
    - Code nodes: Custom logic for embedding storage and memory management
    - Tool orchestration: Chain document parser, chunker, embedder tools
    """
    
    @classmethod
    def create_workflow_config(cls) -> WorkflowConfig:
        """Create workflow configuration with conditional, loop, and code nodes."""
        
        # 1. CONDITIONAL NODE: Check if documents are valid for processing
        document_validation = ConditionNodeConfig(
            id="validate_documents",
            type="condition",
            expression="len(uploaded_files) > 0 and all(f.endswith(('.pdf', '.txt', '.docx')) for f in uploaded_files)",
            condition_type="python_expression",
            description="Validate uploaded documents are supported file types"
        )
        
        # 2. TOOL NODE: Parse documents 
        document_parser = ToolNodeConfig(
            id="parse_documents",
            type="tool",
            tool_name="document_parser",
            tool_args={
                "file_paths": "{{uploaded_files}}"  # Template will be filled at runtime
            },
            description="Extract text content from uploaded documents"
        )
        
        # 3. CONDITIONAL NODE: Check if parsing was successful
        parsing_check = ConditionNodeConfig(
            id="check_parsing_success", 
            type="condition",
            expression="parse_documents.success and len(parse_documents.documents) > 0",
            condition_type="node_output",
            description="Verify documents were successfully parsed"
        )
        
        # 4. LOOP NODE: Process each document individually for optimal chunking
        document_loop = LoopNodeConfig(
            id="process_each_document",
            type="loop",
            items_source="parse_documents.documents",
            loop_variable="current_document",
            max_iterations=10,  # Safety limit
            description="Process each parsed document individually"
        )
        
        # 5. TOOL NODE: Intelligent chunking (inside loop)
        chunking_tool = ToolNodeConfig(
            id="chunk_document",
            type="tool", 
            tool_name="intelligent_chunker",
            tool_args={
                "documents": ["{{current_document}}"],  # Single document from loop
                "chunk_size": 1200,
                "overlap_size": 200,
                "strategy": "semantic"
            },
            description="Create intelligent chunks preserving semantic boundaries"
        )
        
        # 6. CODE NODE: Custom embedding and memory storage logic
        embedding_storage = CodeNodeConfig(
            id="embed_and_store",
            type="code",
            code='''
# Custom logic for embedding and storing in memory
import asyncio
from ice_sdk.services.locator import ServiceLocator

async def embed_and_store_chunks(chunks, document_collection="default"):
    """Custom embedding and storage logic."""
    
    print(f"🧠 Processing {len(chunks)} chunks for embedding...")
    
    # Get LLM service for embeddings
    llm_service = ServiceLocator.get("llm_service")
    stored_chunks = []
    
    for chunk in chunks:
        try:
            # Create embedding using LLM service (simulated)
            chunk_text = chunk["content"]
            
            # In real implementation, would generate actual embeddings
            # embedding = await llm_service.create_embedding(chunk_text)
            
            # Simulate embedding storage
            stored_chunk = {
                "chunk_id": chunk["chunk_id"],
                "content": chunk_text,
                "embedding": f"embedding_vector_{chunk['chunk_id']}",  # Simulated
                "metadata": {
                    "source_file": chunk["source_metadata"]["filename"],
                    "chunk_index": chunk["chunk_index"],
                    "word_count": chunk["word_count"],
                    "document_collection": document_collection
                }
            }
            stored_chunks.append(stored_chunk)
            
        except Exception as e:
            print(f"⚠️ Failed to embed chunk {chunk.get('chunk_id', 'unknown')}: {e}")
    
    print(f"✅ Successfully embedded {len(stored_chunks)} chunks")
    
    return {
        "embedded_chunks": stored_chunks,
        "total_embedded": len(stored_chunks),
        "collection": document_collection
    }

# Execute the embedding logic
result = await embed_and_store_chunks(
    chunks=chunk_document.chunks,
    document_collection=context.get("document_collection", "default")
)

# Return result for next nodes
return result
            ''',
            timeout=30,
            description="Custom embedding and memory storage with error handling"
        )
        
        # 7. CONDITIONAL NODE: Check embedding success and decide next action
        embedding_check = ConditionNodeConfig(
            id="check_embedding_success",
            type="condition", 
            expression="embed_and_store.total_embedded > 0",
            condition_type="node_output",
            description="Verify chunks were successfully embedded"
        )
        
        # 8. LLM NODE: Generate processing summary 
        processing_summary = LLMOperatorConfig(
            id="generate_summary",
            type="llm",
            prompt="""You are a document processing assistant. Generate a helpful summary of the document processing results.

PROCESSING RESULTS:
- Documents parsed: {{parse_documents.total_parsed}}
- Total chunks created: {{process_each_document.total_iterations}}
- Chunks embedded: {{embed_and_store.total_embedded}}
- Document collection: {{embed_and_store.collection}}

Create a friendly summary for the user explaining:
1. What documents were processed
2. How many chunks were created  
3. That their chatbot is ready to answer questions
4. Suggest they try asking about the document content

Keep it concise and encouraging.""",
            llm_config=LLMConfig(
                provider=ModelProvider.OPENAI,
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=300
            ),
            description="Generate user-friendly processing summary"
        )
        
        # 9. CODE NODE: Final setup and agent activation
        agent_setup = CodeNodeConfig(
            id="activate_chatbot",
            type="code",
            code='''
# Activate the document chatbot with processed knowledge
print("🤖 Activating DocumentChatAgent with processed knowledge...")

# In real implementation, would register agent with memory system
agent_config = {
    "session_id": context.get("session_id", "default"),
    "document_collection": embed_and_store["collection"],
    "total_documents": parse_documents["total_parsed"],
    "total_chunks": embed_and_store["total_embedded"],
    "status": "ready"
}

print(f"✅ Chatbot activated for session {agent_config['session_id']}")
print(f"📚 Knowledge base contains {agent_config['total_chunks']} chunks")

return {
    "chatbot_status": "active",
    "agent_config": agent_config,
    "ready_message": "Your document chatbot is ready! Ask me questions about your uploaded documents."
}
            ''',
            description="Activate document chatbot with processed knowledge"
        )
        
        # Create workflow configuration
        workflow_config = WorkflowConfig(
            id="document_processing_workflow",
            name="Document Processing with Control Flow",
            description="Sophisticated document processing showcasing conditional, loop, and code nodes",
            nodes=[
                document_validation,
                document_parser,
                parsing_check,
                document_loop,
                chunking_tool,
                embedding_storage,
                embedding_check,
                processing_summary,
                agent_setup
            ],
            edges=[
                # Main processing flow
                {"from": "validate_documents", "to": "parse_documents", "condition": "true"},
                {"from": "parse_documents", "to": "check_parsing_success"},
                {"from": "check_parsing_success", "to": "process_each_document", "condition": "true"},
                
                # Loop processing
                {"from": "process_each_document", "to": "chunk_document", "context": "loop"},
                {"from": "chunk_document", "to": "embed_and_store", "context": "loop"},
                {"from": "embed_and_store", "to": "check_embedding_success", "context": "loop"},
                
                # Final processing
                {"from": "check_embedding_success", "to": "generate_summary", "condition": "true"},
                {"from": "generate_summary", "to": "activate_chatbot"},
                
                # Error paths
                {"from": "validate_documents", "to": "generate_error_message", "condition": "false"},
                {"from": "check_parsing_success", "to": "generate_error_message", "condition": "false"},
                {"from": "check_embedding_success", "to": "generate_error_message", "condition": "false"}
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "uploaded_files": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "List of uploaded file paths"
                    },
                    "session_id": {
                        "type": "string",
                        "default": "default",
                        "description": "User session identifier"
                    },
                    "document_collection": {
                        "type": "string", 
                        "default": "default",
                        "description": "Document collection name"
                    }
                },
                "required": ["uploaded_files"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "chatbot_status": {"type": "string"},
                    "agent_config": {"type": "object"},
                    "processing_summary": {"type": "string"},
                    "ready_message": {"type": "string"}
                }
            }
        )
        
        return workflow_config
    
    @classmethod
    def create_simple_chat_workflow(cls) -> WorkflowConfig:
        """Create simpler workflow for ongoing chat interactions."""
        
        # 1. TOOL NODE: Search relevant chunks
        semantic_search = ToolNodeConfig(
            id="search_documents",
            type="tool",
            tool_name="semantic_search",
            tool_args={
                "query": "{{user_question}}",
                "document_collection": "{{document_collection}}",
                "limit": 5
            }
        )
        
        # 2. CONDITIONAL NODE: Check if relevant content found
        content_check = ConditionNodeConfig(
            id="check_content_found",
            type="condition",
            expression="len(search_documents.results) > 0",
            condition_type="node_output"
        )
        
        # 3. LLM NODE: Generate response with context
        contextual_response = LLMOperatorConfig(
            id="generate_response",
            type="llm",
            prompt="""You are a helpful document assistant. Answer the user's question based on the provided document context.

DOCUMENT CONTEXT:
{{search_documents.results}}

PREVIOUS CONVERSATION:
{{conversation_history}}

USER QUESTION: {{user_question}}

Provide a helpful, accurate answer based on the document content. If the documents don't contain relevant information, say so politely.""",
            llm_config=LLMConfig(
                provider=ModelProvider.OPENAI,
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=500
            )
        )
        
        return WorkflowConfig(
            id="document_chat_workflow",
            name="Document Chat Interaction",
            description="Handle user questions with document context",
            nodes=[semantic_search, content_check, contextual_response],
            edges=[
                {"from": "search_documents", "to": "check_content_found"},
                {"from": "check_content_found", "to": "generate_response", "condition": "true"}
            ]
        ) 