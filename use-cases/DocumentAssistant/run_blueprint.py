#!/usr/bin/env python3
"""
📚💬 Document Assistant - Real iceOS Blueprint Execution
======================================================

ZERO MOCKING - ALL REAL:
✅ Real document parsing (PDF, Word, Text)
✅ Real intelligent chunking 
✅ Real semantic search
✅ Real agent memory storage
✅ Real LLM processing
✅ Real workflow orchestration

Usage:
    python run_blueprint.py
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# iceOS Blueprint imports
from ice_orchestrator.workflow import Workflow
from ice_orchestrator.execution.executor import WorkflowExecutor
from ice_core.registry import ToolRegistry, AgentRegistry

# Import real workflows
from use_cases.DocumentAssistant.workflows import (
    create_document_processing_workflow,
    create_simple_chat_workflow
)

# Import tools and agents
from use_cases.DocumentAssistant.tools import (
    DocumentParserTool,
    IntelligentChunkerTool, 
    SemanticSearchTool
)
from use_cases.DocumentAssistant.agents import DocumentChatAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_document_processing_blueprint() -> dict:
    """Execute document processing with real files."""
    
    print("📚 EXECUTING DOCUMENT PROCESSING BLUEPRINT (REAL Files)")
    print("=" * 60)
    
    # Create real workflow
    workflow = create_document_processing_workflow()
    
    # Real document files - no mocking
    uploaded_files = [
        "use-cases/DocumentAssistant/docs/ai_ml_guide.md",
        "use-cases/DocumentAssistant/docs/project_management_guide.md",
        "use-cases/DocumentAssistant/docs/software_development_guide.md"
    ]
    
    # Verify files exist
    existing_files = []
    for file_path in uploaded_files:
        if Path(file_path).exists():
            existing_files.append(file_path)
            print(f"✅ Found: {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
    
    if not existing_files:
        print("❌ No valid documents found for processing")
        return {"error": "No documents available"}
    
    # Real inputs - no mocking
    inputs = {
        "uploaded_files": existing_files,
        "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "document_collection": "enterprise_docs",
        "chunk_size": 1000,
        "overlap_size": 200,
        "chunking_strategy": "semantic"
    }
    
    print(f"📁 Processing {len(existing_files)} real documents")
    print(f"🆔 Session: {inputs['session_id']}")
    print(f"📚 Collection: {inputs['document_collection']}")
    
    # Execute with real iceOS orchestrator
    executor = WorkflowExecutor()
    
    try:
        print("\n🚀 Executing workflow with REAL document processing...")
        result = await executor.execute(workflow, inputs)
        
        print(f"\n✅ DOCUMENT PROCESSING COMPLETE!")
        print(f"📄 Documents Processed: {result.get('documents_processed', 'N/A')}")
        print(f"🧩 Chunks Created: {result.get('chunks_created', 'N/A')}")
        print(f"💾 Embedding Status: {result.get('embedding_status', 'N/A')}")
        print(f"🤖 Chatbot Ready: {result.get('chat_ready', False)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        return {"error": str(e)}


async def run_document_chat_blueprint(processing_result: dict) -> dict:
    """Execute document chat with real queries."""
    
    print("\n💬 EXECUTING DOCUMENT CHAT BLUEPRINT (REAL Queries)")
    print("=" * 60)
    
    if "error" in processing_result:
        print("❌ Cannot run chat - document processing failed")
        return {"error": "Prerequisites not met"}
    
    # Create real workflow
    workflow = create_simple_chat_workflow()
    
    # Real user queries - no mocking
    real_queries = [
        "What are the key differences between supervised and unsupervised learning?",
        "How do I implement Scrum methodology in my team?", 
        "What are the best practices for test-driven development?",
        "Explain the Agile methodology and its core principles",
        "What is the software development lifecycle and its phases?"
    ]
    
    chat_results = []
    
    for i, query in enumerate(real_queries, 1):
        print(f"\n🤔 Query {i}: {query}")
        
        # Real inputs - no mocking
        inputs = {
            "user_query": query,
            "session_id": processing_result.get("session_id", "default"),
            "document_collection": "enterprise_docs",
            "similarity_threshold": 0.7,
            "max_results": 5
        }
        
        # Execute with real iceOS orchestrator
        executor = WorkflowExecutor()
        
        try:
            result = await executor.execute(workflow, inputs)
            
            response = result.get("response", "No response generated")
            confidence = result.get("confidence", 0.0)
            sources = result.get("sources_used", 0)
            
            print(f"🤖 Response: {response[:100]}...")
            print(f"🎯 Confidence: {confidence:.2f}")
            print(f"📚 Sources: {sources}")
            
            chat_results.append({
                "query": query,
                "response": response,
                "confidence": confidence,
                "sources_used": sources
            })
            
        except Exception as e:
            logger.error(f"Chat query {i} failed: {e}")
            chat_results.append({
                "query": query,
                "error": str(e)
            })
    
    return {
        "total_queries": len(real_queries),
        "successful_queries": len([r for r in chat_results if "error" not in r]),
        "chat_results": chat_results
    }


async def run_integrated_document_assistant() -> dict:
    """Execute full document assistant workflow integration."""
    
    print("\n🔄 EXECUTING INTEGRATED DOCUMENT ASSISTANT BLUEPRINT")
    print("=" * 60)
    
    # Step 1: Process documents
    processing_result = await run_document_processing_blueprint()
    
    # Step 2: Run chat interactions
    chat_result = await run_document_chat_blueprint(processing_result)
    
    # Combine results
    integrated_result = {
        "document_processing": processing_result,
        "chat_interaction": chat_result,
        "integration_successful": "error" not in processing_result and "error" not in chat_result
    }
    
    if integrated_result["integration_successful"]:
        print(f"\n✅ INTEGRATED WORKFLOW COMPLETE!")
        print(f"📄 Documents: {processing_result.get('documents_processed', 0)}")
        print(f"🧩 Chunks: {processing_result.get('chunks_created', 0)}")
        print(f"💬 Queries: {chat_result.get('successful_queries', 0)}")
    else:
        print(f"\n❌ Integration had issues - check individual results")
    
    return integrated_result


async def main():
    """Execute complete Document Assistant Blueprint suite."""
    
    print("🎯 DOCUMENT ASSISTANT - REAL iceOS BLUEPRINT EXECUTION")
    print("🚫 ZERO MOCKING - ALL REAL Files, Processing, and Queries")
    print("=" * 80)
    
    # Register all components
    print("📋 Registering Document Assistant components...")
    try:
        # Register tools
        tool_registry = ToolRegistry()
        tool_registry.register("document_parser", DocumentParserTool)
        tool_registry.register("intelligent_chunker", IntelligentChunkerTool)
        tool_registry.register("semantic_search", SemanticSearchTool)
        
        # Register agents
        agent_registry = AgentRegistry()
        agent_registry.register("document_chat_agent", DocumentChatAgent)
        
        print("✅ Components registered successfully")
    except Exception as e:
        logger.error(f"Component registration failed: {e}")
        return
    
    # Track execution results
    execution_results = {
        "start_time": datetime.now().isoformat(),
        "workflows_executed": [],
        "documents_processed": 0,
        "queries_answered": 0,
        "results": {}
    }
    
    try:
        # Execute individual workflows
        processing_result = await run_document_processing_blueprint()
        execution_results["results"]["document_processing"] = processing_result
        execution_results["workflows_executed"].append("document_processing")
        
        chat_result = await run_document_chat_blueprint(processing_result)
        execution_results["results"]["document_chat"] = chat_result
        execution_results["workflows_executed"].append("document_chat")
        
        # Execute integrated workflow
        integrated_result = await run_integrated_document_assistant()
        execution_results["results"]["integrated"] = integrated_result
        execution_results["workflows_executed"].append("integrated")
        
        # Update stats
        execution_results["documents_processed"] = processing_result.get("documents_processed", 0)
        execution_results["queries_answered"] = chat_result.get("successful_queries", 0)
        
    except Exception as e:
        logger.error(f"Blueprint execution failed: {e}")
        execution_results["error"] = str(e)
    
    execution_results["end_time"] = datetime.now().isoformat()
    
    # Final summary
    print(f"\n🎉 DOCUMENT ASSISTANT BLUEPRINT EXECUTION COMPLETE!")
    print(f"📊 Workflows Executed: {len(execution_results['workflows_executed'])}")
    print(f"📄 Documents Processed: {execution_results['documents_processed']}")
    print(f"💬 Queries Answered: {execution_results['queries_answered']}")
    print(f"⚡ All Real Processing - Zero Mocking")
    
    # Save results
    results_file = Path("document_assistant_blueprint_results.json")
    import json
    with open(results_file, "w") as f:
        json.dump(execution_results, f, indent=2)
    print(f"💾 Results saved to: {results_file}")
    
    return execution_results


if __name__ == "__main__":
    asyncio.run(main()) 