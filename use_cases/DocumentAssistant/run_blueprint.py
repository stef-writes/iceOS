#!/usr/bin/env python3
"""
📚💬 Document Assistant - MCP API Blueprint Execution
===================================================

Uses the proper MCP API layer for blueprint execution instead of 
manual workflow debugging. This is what the API was designed for!

Usage:
    python run_blueprint.py
"""

import asyncio
import logging
import requests
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# iceOS MCP API models
from ice_core.models.mcp import Blueprint, NodeSpec

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_document_chat_blueprint(user_query: str, session_id: str) -> Blueprint:
    """Create a proper blueprint for document chat using MCP API."""
    
    return Blueprint(
        blueprint_id=f"document_chat_{session_id}_{hash(user_query) % 10000}",
        nodes=[
            # Node 1: Search documents
            NodeSpec(
                id="search_documents",
                type="tool",
                tool_name="semantic_search",
                tool_args={
                    "query": user_query,
                    "document_collection": "enterprise_docs",
                    "limit": 5,
                    "similarity_threshold": 0.7
                },
                input_schema={"query": "string"},
                output_schema={"results": "array"}
            ),
            # Node 2: Generate response with LLM
            NodeSpec(
                id="chat_response",
                type="llm",
                model="gpt-4o",
                dependencies=["search_documents"],
                prompt=f"""You are a helpful assistant answering questions about uploaded documents.

User Question: {user_query}

Document Context:
{{{{#search_documents.results}}}}
- {{{{content}}}}
{{{{/search_documents.results}}}}

Based on the document context above, provide a comprehensive and helpful answer to the user's question.

Guidelines:
- Use specific information from the documents when available
- Be concise but comprehensive  
- If you can't find relevant information, say so clearly
- Cite which documents contain the information when possible

Response:""",
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                input_schema={"prompt": "string"},
                output_schema={
                    "response": "string",
                    "confidence": "number",
                    "sources_used": "integer"
                }
            )
        ],
        metadata={
            "session_id": session_id,
            "query": user_query,
            "timestamp": datetime.now().isoformat()
        }
    )


async def execute_via_mcp_api(blueprint: Blueprint, api_base: str = "http://localhost:8000/api/v1") -> Dict[str, Any]:
    """Execute blueprint via MCP API endpoints (the proper way!)."""
    
    print(f"🚀 Executing blueprint {blueprint.blueprint_id} via MCP API...")
    
    try:
        # Method 1: Direct blueprint execution via /runs endpoint
        run_request = {
            "blueprint": blueprint.model_dump(),
            "options": {
                "max_parallel": 3
            }
        }
        
        response = requests.post(
            f"{api_base}/mcp/runs",
            json=run_request,
            headers={"Content-Type": "application/json"},
            timeout=70.0
        )
        
        if response.status_code == 202:  # Accepted
            result = response.json()
            print(f"✅ Blueprint submitted! Run ID: {result.get('run_id')}")
            
            # Get the status endpoint to check completion
            status_endpoint = result.get('status_endpoint', '')
            if status_endpoint:
                print(f"📊 Checking status at: {status_endpoint}")
                # Poll for completion (simple approach)
                import time
                for _ in range(30):  # 30 second timeout
                    time.sleep(1)
                    try:
                        status_response = requests.get(f"http://localhost:8000{status_endpoint}", timeout=5.0)
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"Status: {status_data.get('status', 'unknown')}")
                            if status_data.get('status') in ['completed', 'failed']:
                                return status_data
                    except:
                        continue
                
                print("⏰ Timeout waiting for completion")
                return {"status": "timeout", "run_id": result.get('run_id')}
            
            return result
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return {"error": f"API error: {response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  API connection failed: {e}")
        print("🔄 Falling back to direct workflow execution...")
        
        # Fallback: Direct workflow execution (if API server not running)
        return await execute_direct_workflow_fallback(blueprint)


async def execute_direct_workflow_fallback(blueprint: Blueprint) -> Dict[str, Any]:
    """Fallback execution if MCP API server is not running."""
    
    print("🔧 Using direct workflow execution as fallback...")
    
    # Import and execute workflows directly (fallback only)
    from use_cases.DocumentAssistant.workflows.document_processing_workflow import create_simple_chat_workflow
    
    workflow = create_simple_chat_workflow()
    
    # Extract context from blueprint metadata
    context = {
        "user_query": blueprint.metadata.get("query", ""),
        "session_id": blueprint.metadata.get("session_id", "default"),
        "document_collection": "enterprise_docs",
        "similarity_threshold": 0.7,
        "max_results": 5
    }
    
    # Set workflow context via context manager
    workflow.context_manager.set_context_from_dict(context)
    
    # Execute workflow
    result = await workflow.execute()
    
    return {
        "status": "completed" if result.success else "failed",
        "output": result.output,
        "error": str(result.error) if hasattr(result, 'error') and result.error else None
    }


async def run_document_chat_demo():
    """Run the Document Assistant demo using proper MCP API layer."""
    
    print("🎯 DOCUMENT ASSISTANT - MCP API BLUEPRINT EXECUTION")
    print("🚀 Using proper API layer (no manual workflow debugging!)")
    print("=" * 80)
    
    # Real queries to test
    queries = [
        "What are the key differences between supervised and unsupervised learning?",
        "How do I implement Scrum methodology in my team?", 
        "What are the best practices for test-driven development?",
        "Explain the Agile methodology and its core principles",
        "What is the software development lifecycle and its phases?"
    ]
    
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n🤔 Query {i}: {query}")
        
        # Create blueprint using MCP API models
        blueprint = create_document_chat_blueprint(query, session_id)
        
        # Execute via MCP API endpoints
        result = await execute_via_mcp_api(blueprint)
        
        if "error" not in result:
            output = result.get("output", {})
            response = output.get("response", "No response generated")
            print(f"🤖 Response: {response[:150]}...")
            
            results.append({
                "query": query,
                "response": response,
                "status": result.get("status", "unknown"),
                "run_id": result.get("run_id")
            })
        else:
            print(f"❌ Error: {result['error']}")
            results.append({
                "query": query,
                "error": result["error"]
            })
    
    # Save results
    results_file = "document_assistant_mcp_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ DEMO COMPLETE!")
    print(f"📊 Queries Processed: {len(queries)}")
    print(f"💾 Results saved to: {results_file}")
    print(f"🚀 Used proper MCP API layer - no manual debugging!")


if __name__ == "__main__":
    asyncio.run(run_document_chat_demo()) 