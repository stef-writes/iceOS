"""DocumentAssistant - Enterprise-grade document processing and chat system.

This module provides reusable tools and agents for document processing workflows.
Designed for maximum reusability across demos and early product builds.
"""

from .tools import DocumentParserTool, IntelligentChunkerTool, SemanticSearchTool
from .agents import DocumentChatAgent

# Export main components for easy reuse
__all__ = [
    "DocumentParserTool",
    "IntelligentChunkerTool", 
    "SemanticSearchTool",
    "DocumentChatAgent"
]

# Component registry for automated registration
TOOLS = [
    DocumentParserTool,
    IntelligentChunkerTool,
    SemanticSearchTool
]

AGENTS = [
    ("document_chat_agent", "use_cases.DocumentAssistant.agents.document_chat_agent")
] 