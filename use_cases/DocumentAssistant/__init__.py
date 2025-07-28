"""DocumentAssistant - Intelligent document processing and chat system."""

# Import all components for registry
from .tools import DocumentParserTool, IntelligentChunkerTool, SemanticSearchTool
from .agents import DocumentChatAgent

# Register tools in the global registry
def initialize_tools():
    """Register DocumentAssistant tools with the global registry."""
    from ice_core.models.enums import NodeType
    from ice_core.unified_registry import registry
    
    try:
        # Register tool instances
        registry.register_instance(NodeType.TOOL, "document_parser", DocumentParserTool())
        registry.register_instance(NodeType.TOOL, "intelligent_chunker", IntelligentChunkerTool())
        registry.register_instance(NodeType.TOOL, "semantic_search", SemanticSearchTool())
        
        print("✅ DocumentAssistant tools registered successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to register DocumentAssistant tools: {e}")
        return False

def initialize_agents():
    """Register DocumentAssistant agents with the global registry."""
    from ice_core.unified_registry import global_agent_registry
    
    try:
        # Register agent classes
        global_agent_registry.register_agent(
            "document_chat_agent", 
            "use_cases.DocumentAssistant.agents.document_chat_agent"
        )
        
        print("✅ DocumentAssistant agents registered successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to register DocumentAssistant agents: {e}")
        return False

def initialize_all(context: str = "standalone") -> bool:
    """Initialize all DocumentAssistant components."""
    print(f"🚀 Initializing DocumentAssistant components (context: {context})...")
    
    tools_ok = initialize_tools()
    agents_ok = initialize_agents()
    
    if tools_ok and agents_ok:
        print("✅ DocumentAssistant initialization complete")
        return True
    else:
        print("❌ DocumentAssistant initialization failed")
        return False

# Export registry information for discovery
AGENT_REGISTRY = [
    ("document_chat_agent", "use_cases.DocumentAssistant.agents.document_chat_agent")
]

__all__ = [
    "DocumentParserTool",
    "IntelligentChunkerTool", 
    "SemanticSearchTool",
    "DocumentChatAgent",
    "initialize_all",
    "AGENT_REGISTRY"
] 