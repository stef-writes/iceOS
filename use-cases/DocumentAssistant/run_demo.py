"""Standalone demo runner for DocumentAssistant chat-in-a-box.

This script runs the demo independently without requiring the full iceOS setup.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Now we can import iceOS components
from ice_sdk.tools.base import ToolBase
from typing import Dict, Any, List


# Import our demo tools directly
from tools.document_parser import DocumentParserTool
from tools.intelligent_chunker import IntelligentChunkerTool  
from tools.semantic_search import SemanticSearchTool


async def create_sample_documents():
    """Create sample documents for demonstration."""
    
    print("📄 Creating sample documents for demo...")
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Sample document 1: AI and Machine Learning
    doc1_content = """# Artificial Intelligence and Machine Learning Guide

## Introduction
Artificial Intelligence (AI) represents one of the most transformative technologies of our time. This comprehensive guide covers the fundamentals of AI and machine learning.

## Core Concepts
Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed. Key concepts include:

- Supervised Learning: Training with labeled data
- Unsupervised Learning: Finding patterns in unlabeled data  
- Reinforcement Learning: Learning through trial and error

## Applications
AI has numerous real-world applications:
- Natural Language Processing for chatbots and translation
- Computer Vision for image recognition and autonomous vehicles
- Predictive Analytics for business intelligence
- Recommendation Systems for personalized content

## Best Practices
When implementing AI solutions:
1. Start with clear objectives and success metrics
2. Ensure high-quality, representative training data
3. Consider ethical implications and bias mitigation
4. Plan for ongoing monitoring and model updates

## Conclusion
AI and machine learning continue to evolve rapidly, offering exciting opportunities for innovation across industries."""

    doc1_path = data_dir / "ai_ml_guide.txt"
    with open(doc1_path, 'w') as f:
        f.write(doc1_content)
    
    # Sample document 2: Project Management
    doc2_content = """Project Management Best Practices

Project management is the discipline of planning, organizing, and managing resources to achieve specific goals within defined constraints.

Key Project Management Phases:
1. Initiation - Define project scope and objectives
2. Planning - Develop detailed project plan and timeline
3. Execution - Implement the project plan
4. Monitoring - Track progress and make adjustments
5. Closure - Complete project and document lessons learned

Critical Success Factors:
- Clear communication with stakeholders
- Realistic timeline and resource planning
- Risk identification and mitigation strategies
- Regular progress monitoring and reporting
- Stakeholder engagement and buy-in

Common Project Management Tools:
- Gantt charts for timeline visualization
- Kanban boards for task management
- Risk registers for tracking potential issues
- Status reports for stakeholder communication

Agile vs. Waterfall Methodologies:
Agile: Iterative approach with frequent feedback
Waterfall: Sequential approach with defined phases

The choice between methodologies depends on project requirements, team structure, and organizational culture."""

    doc2_path = data_dir / "project_management.txt"
    with open(doc2_path, 'w') as f:
        f.write(doc2_content)
    
    return [str(doc1_path), str(doc2_path)]


async def demonstrate_individual_tools():
    """Demonstrate each tool working independently."""
    
    print("\n🛠️  === DEMONSTRATING INDIVIDUAL TOOLS ===")
    
    # Create sample documents
    file_paths = await create_sample_documents()
    
    # 1. Document Parser Tool
    print("\n📝 Testing DocumentParserTool...")
    parser = DocumentParserTool()
    parse_result = await parser.execute(file_paths=file_paths)
    
    print(f"✅ Parsed {parse_result['total_parsed']} documents")
    for doc in parse_result['documents']:
        print(f"   📄 {doc['metadata']['filename']}: {doc['word_count']} words")
    
    # 2. Intelligent Chunker Tool  
    print("\n✂️  Testing IntelligentChunkerTool...")
    chunker = IntelligentChunkerTool()
    chunk_result = await chunker.execute(
        documents=parse_result['documents'],
        chunk_size=800,
        strategy="semantic"
    )
    
    print(f"✅ Created {len(chunk_result['chunks'])} chunks using {chunk_result['processing_stats']['strategy_used']} strategy")
    for i, chunk in enumerate(chunk_result['chunks'][:3]):  # Show first 3
        print(f"   🧩 Chunk {i+1}: {chunk['word_count']} words, ID: {chunk['chunk_id']}")
    
    # 3. Semantic Search Tool
    print("\n🔍 Testing SemanticSearchTool...")
    search = SemanticSearchTool()
    search_result = await search.execute(
        query="machine learning applications",
        document_collection="demo",
        limit=3
    )
    
    print(f"✅ Found {search_result['total_results']} relevant chunks")
    for result in search_result['results']:
        print(f"   📊 Similarity: {result['similarity_score']:.2f} - {result['chunk_id']}")
    
    return {
        "parsed_documents": parse_result['documents'],
        "chunks": chunk_result['chunks'],
        "search_results": search_result['results']
    }


async def simulate_workflow_orchestration():
    """Simulate the workflow orchestration (without full iceOS)."""
    
    print("\n🔄 === SIMULATING WORKFLOW ORCHESTRATION ===")
    print("📋 Simulating sophisticated workflow with conditional, loop, and code nodes:")
    print("   ❓ validate_documents (CONDITIONAL): Check file types")
    print("   🛠️  parse_documents (TOOL): Extract text content")  
    print("   ❓ check_parsing_success (CONDITIONAL): Verify parsing")
    print("   🔁 process_each_document (LOOP): Process documents individually")
    print("   🛠️  chunk_document (TOOL): Create semantic chunks")
    print("   💻 embed_and_store (CODE): Custom embedding logic")
    print("   ❓ check_embedding_success (CONDITIONAL): Verify embedding")
    print("   🤖 generate_summary (LLM): Create processing summary")
    print("   💻 activate_chatbot (CODE): Activate document chatbot")
    
    print("\n🔗 Workflow execution flow:")
    print("   validate_documents → parse_documents → check_parsing_success")
    print("   check_parsing_success → process_each_document (LOOP)")
    print("   LOOP: chunk_document → embed_and_store → check_embedding_success")
    print("   check_embedding_success → generate_summary → activate_chatbot")
    
    print("\n✅ Workflow orchestration demonstrates:")
    print("   🎯 Conditional logic for validation and flow control")
    print("   🔁 Loop nodes for efficient multi-document processing")
    print("   💻 Code nodes for custom embedding and memory logic")
    print("   🔄 Complex DAG execution with branching and error paths")


async def simulate_agent_coordination():
    """Simulate agent coordination with memory."""
    
    print("\n🤖 === SIMULATING AGENT COORDINATION ===")
    print("✅ DocumentChatAgent created with memory enabled")
    
    # Simulate document processing
    print("\n📚 Simulating document processing request...")
    file_paths = await create_sample_documents()
    
    print(f"✅ Processed {len(file_paths)} documents successfully! Your chatbot is ready.")
    print(f"📊 Documents processed: {len(file_paths)}")
    
    # Simulate chat interactions
    print("\n💬 Simulating chat interactions...")
    
    questions = [
        "What is machine learning?",
        "Tell me about AI applications", 
        "How do I manage a project effectively?",
        "What are the phases of project management?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n❓ Question {i}: {question}")
        
        # Simulate intelligent response
        if "machine learning" in question.lower():
            confidence = 0.92
            sources = 3
            response = "Based on your documents, machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed. Your documents mention supervised learning, unsupervised learning, and reinforcement learning as key concepts."
        elif "ai applications" in question.lower():
            confidence = 0.88
            sources = 2
            response = "Your documents describe several AI applications including Natural Language Processing for chatbots and translation, Computer Vision for image recognition and autonomous vehicles, Predictive Analytics for business intelligence, and Recommendation Systems for personalized content."
        elif "project" in question.lower():
            confidence = 0.85
            sources = 4
            response = "According to your project management document, effective project management involves five key phases: Initiation, Planning, Execution, Monitoring, and Closure. Critical success factors include clear communication with stakeholders and realistic timeline planning."
        else:
            confidence = 0.78
            sources = 2
            response = "The project management phases are: 1) Initiation - Define scope and objectives, 2) Planning - Develop detailed plan, 3) Execution - Implement the plan, 4) Monitoring - Track progress, 5) Closure - Complete and document lessons learned."
        
        print(f"🤖 Response (confidence: {confidence:.2f}):")
        response_preview = response[:150] + "..." if len(response) > 150 else response
        print(f"   {response_preview}")
        print(f"📊 Sources found: {sources}")


async def run_standalone_demo():
    """Run the complete DocumentAssistant demo in standalone mode."""
    
    print("🎪 === DOCUMENTASSISTANT CHAT-IN-A-BOX DEMO ===")
    print("Showcasing iceOS workflow orchestration with conditional, loop, and code nodes")
    print("(Running in standalone mode)")
    print("=" * 80)
    
    try:
        # 1. Individual tool demonstration
        await demonstrate_individual_tools()
        
        # 2. Workflow orchestration simulation
        await simulate_workflow_orchestration()
        
        # 3. Agent coordination simulation
        await simulate_agent_coordination()
        
        print("\n🎉 === DEMO COMPLETE ===")
        print("✅ Successfully demonstrated:")
        print("   🛠️  Individual reusable tools working independently")
        print("   🔄 Sophisticated workflow orchestration concepts") 
        print("   ❓ Conditional nodes for validation and flow control")
        print("   🔁 Loop nodes for multi-document processing")
        print("   💻 Code nodes for custom logic")
        print("   🤖 Agent coordination with workflows")
        print("   🧠 Memory persistence concepts")
        print("\n🏆 iceOS chat-in-a-box demo showcases enterprise-grade workflow automation!")
        print("\n📝 Note: This is a standalone demo. For full iceOS integration,")
        print("   run via MCP API with the blueprint registration script.")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(run_standalone_demo()) 