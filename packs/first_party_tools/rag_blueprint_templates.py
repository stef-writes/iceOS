from __future__ import annotations

"""Blueprint templates for RAG-style assistants.

These are plain Python helpers that return JSON-serializable blueprints the
client can submit. Keeping them close to tools avoids vague file naming.
"""

from typing import Any, Dict, List


def rag_chat_blueprint(
    *, model: str = "gpt-4o", scope: str = "kb", top_k: int = 5
) -> Dict[str, Any]:
    """Return a minimal RAG chat assistant blueprint.

    Nodes:
    - memory_search_tool → LLM → (optional) memory_write_tool as transcript
    """

    nodes: List[Dict[str, Any]] = [
        {
            "id": "search",
            "type": "tool",
            "tool_name": "memory_search_tool",
            "tool_args": {
                "query": "{{ inputs.query }}",
                "scope": scope,
                "limit": top_k,
                "org_id": "{{ inputs.org_id }}",
            },
            "dependencies": [],
        },
        {
            "id": "llm",
            "type": "llm",
            "model": model,
            "prompt": (
                "Use the retrieved context to answer.\n"
                "Context: {{ search.results }}\n"
                "Question: {{ inputs.query }}\n"
            ),
            "llm_config": {"provider": "openai", "model": model},
            "output_schema": {"text": "string"},
            "dependencies": ["search"],
        },
        {
            "id": "write",
            "type": "tool",
            "tool_name": "memory_write_tool",
            "tool_args": {
                "key": "chat:{{ inputs.query }}",
                "content": "{{ llm.response }}",
                "scope": scope,
                "org_id": "{{ inputs.org_id }}",
                "user_id": "{{ inputs.user_id }}",
            },
            "dependencies": ["llm"],
        },
    ]
    return {"schema_version": "1.2.0", "nodes": nodes}
