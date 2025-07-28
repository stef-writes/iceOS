"""Workflow definitions for DocumentAssistant demo.

These workflows showcase iceOS's orchestration capabilities with
conditional nodes, loop nodes, and code nodes.
"""

from .document_processing_workflow import (
    create_document_processing_workflow,
    create_simple_chat_workflow
)

__all__ = [
    "create_document_processing_workflow",
    "create_simple_chat_workflow"
] 