from __future__ import annotations

from typing import Any, Mapping

from ice_core.models.mcp import Blueprint, NodeSpec


def rag_chat_blueprint_agent(
    *,
    model: str,
    scope: str,
    top_k: int = 5,
    with_citations: bool = False,
) -> Blueprint:
    """Return a Blueprint that performs RAG chat (search + LLM) using real LLM.

    Parameters
    ----------
    model : str
            LLM model name (e.g., "gpt-4o").
    scope : str
            Memory scope key for semantic search.
    top_k : int
            Number of retrieved items.
    with_citations : bool
            Whether to include citations in the LLM response.

    Returns
    -------
    Blueprint
            Executable blueprint.
    """

    nodes: list[Mapping[str, Any]] = [
        {
            "id": "recent",
            "type": "tool",
            "tool_name": "recent_session_tool",
            "tool_args": {
                "session_id": "{{ inputs.session_id }}",
                "scope": scope,
                "org_id": "{{ inputs.org_id }}",
                "limit": 5,
            },
            "dependencies": [],
        },
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
                "You are a helpful assistant. Use the search results and recent chat turns to answer.\n"
                "Query: {{ inputs.query }}\n"
                "Recent session items: {{ recent.items }}\n"
                "Search results: {{ search.results }}\n"
            ),
            "llm_config": {
                "provider": "openai",
                "model": model,
                "citations": with_citations,
            },
            "dependencies": ["recent", "search"],
            "output_schema": {"text": "string"},
        },
        {
            "id": "write",
            "type": "tool",
            "tool_name": "memory_write_tool",
            "tool_args": {
                "key": "chat:{{ inputs.session_id }}:{{ inputs.query }}",
                "content": "{{ llm.text }}",
                "scope": scope,
                "org_id": "{{ inputs.org_id }}",
                "user_id": "{{ inputs.user_id }}",
            },
            "dependencies": ["llm"],
        },
    ]

    return Blueprint(
        schema_version="1.2.0",
        metadata={
            "draft_name": "rag_agent",
            # Studio UI hints (progressive disclosure)
            "ui": {
                "inputs": [
                    {
                        "name": "query",
                        "label": "Ask a question",
                        "type": "string",
                        "required": True,
                        "group": "basic",
                        "help": "What do you want to know?",
                    },
                    {
                        "name": "session_id",
                        "label": "Session",
                        "type": "string",
                        "required": False,
                        "group": "basic",
                        "default": "chat_session",
                        "help": "Use the same value across turns for conversation memory.",
                    },
                    {
                        "name": "style",
                        "label": "Style",
                        "type": "string",
                        "required": False,
                        "group": "advanced",
                        "default": "concise",
                        "enum": ["concise", "detailed", "bullet"],
                    },
                    {
                        "name": "tone",
                        "label": "Tone",
                        "type": "string",
                        "required": False,
                        "group": "advanced",
                        "default": "neutral",
                        "enum": ["neutral", "friendly", "formal"],
                    },
                    {
                        "name": "org_id",
                        "label": "Organization",
                        "type": "string",
                        "required": False,
                        "group": "advanced",
                    },
                    {
                        "name": "user_id",
                        "label": "User",
                        "type": "string",
                        "required": False,
                        "group": "advanced",
                    },
                ],
                # Design-time knobs (applied when composing the workflow; not execution inputs)
                "design": {
                    "model": model,
                    "scope": scope,
                    "top_k": top_k,
                    "with_citations": with_citations,
                    "profiles": {
                        "quick": {"top_k": 3, "with_citations": False},
                        "conversational": {"top_k": 5, "with_citations": False},
                        "research": {"top_k": 8, "with_citations": True},
                    },
                },
            },
        },
        nodes=[NodeSpec.model_validate(n) for n in nodes],
    )
