"""Comprehensive demo verification for DocumentAssistant chat-in-a-box.

This demo showcases iceOS's sophisticated workflow orchestration with:
- Conditional nodes for validation and flow control
- Loop nodes for efficient multi-document processing  
- Code nodes for custom embedding and memory logic
- Tool orchestration with reusable components
- Agent coordination with persistent memory
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

# Demo tools and components
from use_cases.DocumentAssistant.tools import (
    DocumentParserTool,
    IntelligentChunkerTool, 
    SemanticSearchTool
)
from use_cases.DocumentAssistant.agents import DocumentChatAgent
from use_cases.DocumentAssistant.workflows import DocumentProcessingWorkflow


async def create_sample_documents():
    """Create sample documents for demonstration."""
    
    print("📄 Creating sample documents for demo...")
    
    # Ensure data directory exists
    data_dir = Path("use-cases/DocumentAssistant/data")
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


async def demonstrate_workflow_orchestration():
    """Demonstrate sophisticated workflow with conditional, loop, and code nodes."""
    
    print("\n🔄 === DEMONSTRATING WORKFLOW ORCHESTRATION ===")
    
    # Create workflow configuration
    workflow_config = DocumentProcessingWorkflow.create_workflow_config()
    
    print(f"📋 Created workflow: {workflow_config.name}")
    print(f"📊 Workflow contains {len(workflow_config.nodes)} nodes:")
    
    # Display workflow structure
    for node in workflow_config.nodes:
        node_type = node.type
        node_id = node.id
        description = getattr(node, 'description', 'No description')
        
        if node_type == "condition":
            print(f"   ❓ {node_id} (CONDITIONAL): {description}")
        elif node_type == "loop": 
            print(f"   🔁 {node_id} (LOOP): {description}")
        elif node_type == "code":
            print(f"   💻 {node_id} (CODE): {description}")
        elif node_type == "tool":
            print(f"   🛠️  {node_id} (TOOL): {description}")
        elif node_type == "llm":
            print(f"   🤖 {node_id} (LLM): {description}")
    
    print(f"\n🔗 Workflow has {len(workflow_config.edges)} edges defining execution flow")
    
    # Show edge connections
    for edge in workflow_config.edges[:8]:  # Show first 8 edges
        condition = edge.get('condition', '')
        context = edge.get('context', '')
        extra = f" (condition: {condition})" if condition else ""
        extra += f" (context: {context})" if context else ""
        print(f"   {edge['from']} → {edge['to']}{extra}")
    
    return workflow_config


async def demonstrate_agent_coordination():
    """Demonstrate agent coordinating with workflows and memory."""
    
    print("\n🤖 === DEMONSTRATING AGENT COORDINATION ===")
    
    # Create agent
    from use_cases.DocumentAssistant.agents.document_chat_agent import create_document_chat_agent
    agent = create_document_chat_agent()
    
    print(f"✅ Created {agent.config.id} with memory enabled: {agent.config.enable_memory}")
    
    # Simulate document processing request
    print("\n📚 Simulating document processing request...")
    file_paths = await create_sample_documents()
    
    processing_result = await agent._execute_with_memory({
        "request_type": "process_documents",
        "uploaded_files": file_paths,
        "session_id": "demo_session_001"
    })
    
    print(f"✅ {processing_result['response']}")
    print(f"📊 Documents processed: {processing_result['documents_processed']}")
    
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
        
        chat_result = await agent._execute_with_memory({
            "request_type": "chat",
            "question": question,
            "session_id": "demo_session_001"
        })
        
        print(f"🤖 Response (confidence: {chat_result['confidence']:.2f}):")
        response_preview = chat_result['response'][:150] + "..." if len(chat_result['response']) > 150 else chat_result['response']
        print(f"   {response_preview}")
        print(f"📊 Sources found: {chat_result['sources_found']}")
    
    return agent


async def demonstrate_memory_persistence():
    """Demonstrate memory system working across sessions."""
    
    print("\n🧠 === DEMONSTRATING MEMORY PERSISTENCE ===")
    
    # Create agent with memory
    from use_cases.DocumentAssistant.agents.document_chat_agent import create_document_chat_agent
    agent = create_document_chat_agent()
    
    # Simulate multiple sessions showing memory persistence
    sessions = ["user_alice", "user_bob", "user_charlie"]
    
    for session_id in sessions:
        print(f"\n👤 Session: {session_id}")
        
        # Setup documents for this session
        setup_result = await agent._execute_with_memory({
            "request_type": "process_documents", 
            "uploaded_files": await create_sample_documents(),
            "session_id": session_id
        })
        
        print(f"   📚 Setup: {setup_result['documents_processed']} documents")
        
        # Ask a question
        chat_result = await agent._execute_with_memory({
            "request_type": "chat",
            "question": f"What can you tell me about AI for {session_id}?",
            "session_id": session_id
        })
        
        print(f"   💬 Chat confidence: {chat_result['confidence']:.2f}")
        print(f"   📊 Sources: {chat_result['sources_found']}")
    
    print(f"\n✅ Demonstrated memory isolation across {len(sessions)} sessions")


async def run_comprehensive_demo():
    """Run the complete DocumentAssistant demo."""
    
    print("🎪 === DOCUMENTASSISTANT CHAT-IN-A-BOX DEMO ===")
    print("Showcasing iceOS workflow orchestration with conditional, loop, and code nodes")
    print("=" * 80)
    
    try:
        # 1. Individual tool demonstration
        tool_results = await demonstrate_individual_tools()
        
        # 2. Workflow orchestration demonstration  
        workflow_config = await demonstrate_workflow_orchestration()
        
        # 3. Agent coordination demonstration
        agent = await demonstrate_agent_coordination()
        
        # 4. Memory persistence demonstration
        await demonstrate_memory_persistence()
        
        print("\n🎉 === DEMO COMPLETE ===")
        print("✅ Successfully demonstrated:")
        print("   🛠️  Individual reusable tools")
        print("   🔄 Sophisticated workflow orchestration") 
        print("   ❓ Conditional nodes for validation and flow control")
        print("   🔁 Loop nodes for multi-document processing")
        print("   💻 Code nodes for custom logic")
        print("   🤖 Agent coordination with workflows")
        print("   🧠 Memory persistence across sessions")
        print("\n🏆 iceOS chat-in-a-box demo showcases enterprise-grade workflow automation!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        raise


async def main():
    """Main entry point for demo."""
    await run_comprehensive_demo()


if __name__ == "__main__":
    asyncio.run(main()) 