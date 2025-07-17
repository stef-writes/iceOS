"""Chat-in-a-Box demo ScriptChain.

This workflow turns a minimal chatbot configuration (tone, KB URL, guardrails)
into a fully-deployed chat widget and returns the <script> snippet ready to be
embedded on any website.
"""

from __future__ import annotations

from typing import List, Union

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.config import LLMConfig
from ice_sdk.models.node_models import AiNodeConfig, KnowledgeNodeConfig, ToolNodeConfig

# ---------------------------------------------------------------------------
# Tool instance (external side-effect) --------------------------------------
# ---------------------------------------------------------------------------
from ice_sdk.tools.web.chat_ui_deployment import ChatUIDeploymentTool

chat_ui_deploy_tool = ChatUIDeploymentTool()

# ---------------------------------------------------------------------------
# Knowledge Base Node -------------------------------------------------------
# ---------------------------------------------------------------------------

knowledge_node = KnowledgeNodeConfig(
    id="kb_lookup",
    type="knowledge",
    name="EnterpriseKB",
    description="""Retrieves relevant context from configured knowledge base.
    
    Args:
        watch_dirs: Directories to monitor for KB updates
        chunk_size: Document chunk size in characters
        chunk_overlap: Overlap between chunks
        label: Namespace for KB content
    """,
    params={
        "watch_dirs": ["{{input.documents_dir}}"],  # Dynamic path from user input
        "chunk_size": 800,
        "chunk_overlap": 120,
        "label": "user-uploaded",
        "auto_parse": True,  # Start ingestion immediately
    },
    output_mappings={"context": "output.context"},
)

# ---------------------------------------------------------------------------
# Nodes ---------------------------------------------------------------------
# ---------------------------------------------------------------------------

prompt_builder_node = AiNodeConfig(
    id="prompt_builder",
    type="ai",
    name="PromptBuilder",
    dependencies=["kb_lookup"],
    model="gpt-4o",
    response_format={"type": "json_object"},  # Required for reliable parsing
    input_schema={
        "type": "object",
        "properties": {
            "tone": {
                "type": "string",
                "description": "Desired chatbot tone (e.g. friendly).",
            },
            "documents_dir": {
                "type": "string",
                "description": "Path to folder containing support documents",
            },
            "guardrails": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of policy guardrails",
            },
        },
        "required": ["tone", "documents_dir", "guardrails"],
    },
    output_schema={},
    prompt=(
        "You are an expert prompt engineer.\n\n"
        "Given documents in {{ documents_dir }}, generate a *strict JSON* payload with the keys:\n"
        "  - system_prompt (string): The final system prompt to govern behaviour.\n"
        "  - sample_pairs (array): Up to 5 example objects with keys 'q' and 'a'.\n\n"
        "# Relevant Context (most recent chunks)\n"
        "{{ kb_lookup.context }}\n\n"
        "# Requirements\n"
        "Tone: {{ tone }}\n"
        "Documents Directory: {{ documents_dir }}\n"
        "Guardrails: {{ guardrails }}\n\n"
        "```json\n"
        "Respond ONLY with valid JSON.\n"
        "```"
    ),
    llm_config=LLMConfig(temperature=0.7),
    output_mappings={
        "system_prompt": "output.system_prompt",
        "examples": "output.sample_pairs",
    },
)

validator_node = AiNodeConfig(
    id="validator",
    type="ai",
    name="SafetyValidator",
    dependencies=["prompt_builder"],
    model="gpt-4o",
    response_format={"type": "json_object"},
    input_schema={
        "type": "object",
        "properties": {
            "system_prompt": {"type": "string"},
            "sample_pairs": {
                "type": "array",
                "items": {"type": "object"},
            },
        },
        "required": ["system_prompt"],
    },
    output_schema={
        "status": str,
    },
    prompt=(
        """You are a compliance and safety auditor.

Use the extracted context to ensure the prompt aligns with knowledge base content.

Given the chatbot system prompt and example Q&A pairs, assess whether the content violates any of the provided guardrails.

If compliant, respond with JSON: {"status": "approved"}.
If violations exist, respond with JSON: {"status": "rejected", "issues": [..]} listing up to 5 issues.

# System Prompt
{{prompt_builder.system_prompt}}

# Example Pairs
{{prompt_builder.examples}}

```json
Respond ONLY with valid JSON containing "status" (approved|rejected). If rejected, include an "issues" array listing up to 5 problems.
```"""
    ),
    llm_config=LLMConfig(temperature=0.0),
    output_mappings={"status": "output.status"},
)

deployment_node = ToolNodeConfig(
    id="deploy",
    type="tool",
    name="DeployChatbot",
    dependencies=["validator"],
    condition="{{validator.status == 'approved'}}",  # Critical safety check
    tool_name=chat_ui_deploy_tool.name,
    tool_args={
        "endpoint": "https://api.example.com/chatbots",
        "api_key": "${CHAT_UI_API_KEY}",  # Placeholder – injected via env
        "config": {
            "system_prompt": "{{prompt_builder.system_prompt}}",
            "examples": "{{prompt_builder.examples}}",
            "validation_status": "{{validator.status}}",
        },
    },
    output_mappings={"embed_script": "output.embed_script"},
)

nodes: List[Union[KnowledgeNodeConfig, AiNodeConfig, ToolNodeConfig]] = [
    knowledge_node,
    prompt_builder_node,
    validator_node,
    deployment_node,
]

# ---------------------------------------------------------------------------
# ScriptChain instance ------------------------------------------------------
# ---------------------------------------------------------------------------

chain = ScriptChain(
    nodes=nodes,
    tools=[chat_ui_deploy_tool],
    name="chat_in_a_box_demo",  # Removed unsupported validate argument
)
