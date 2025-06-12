# This file is the single source of truth for prompt and tool preamble logic.
import logging
from typing import Optional

from ice_sdk.models.config import LLMConfig
from ice_sdk.models.node_models import NodeConfig
from ice_orchestrator.nodes.constants import TOOL_INSTRUCTION
from ice_sdk.utils.token_counter import TokenCounter

# Standalone function for building the tool preamble


def build_tool_preamble(tools: list) -> str:
    """Generate a human-readable preamble describing available tools, their parameters, and usage examples."""
    if not tools:
        return ""
    lines = [TOOL_INSTRUCTION, "\nYou have access to the following tools:"]
    for tool in tools:
        params = tool.get("parameters_schema", {}).get("properties", {})
        required = set(tool.get("parameters_schema", {}).get("required", []))
        param_strs = []
        for k, v in params.items():
            typ = v.get("type", "unknown")
            desc = v.get("description", "")
            req = "required" if k in required else "optional"
            param_strs.append(f"{k} ({typ}, {req}){': ' + desc if desc else ''}")
        param_str = ", ".join(param_strs) if param_strs else "No parameters."
        lines.append(f"- {tool['name']}: {tool['description']} Parameters: {param_str}")
        # Add usage example if present
        usage_example = tool.get("usage_example")
        if usage_example:
            lines.append("  Example:")
            lines.append("  " + usage_example.strip().replace("\n", "\n  "))
    return "\n".join(lines) + "\n\n"


# Standalone function for preparing the prompt


async def prepare_prompt(
    config: NodeConfig,
    context_manager,
    llm_config: LLMConfig,
    tool_service,
    inputs: dict,
    workflow_context=None,
) -> str:
    template = config.prompt
    selected_contexts = {}
    # Filter inputs based on selection
    if config.input_selection:
        selected_contexts = {
            k: v for k, v in inputs.items() if k in config.input_selection
        }
    else:
        selected_contexts = inputs
    # Apply context rules and format inputs
    formatted_inputs = {}
    for input_id, context in selected_contexts.items():
        rule = config.context_rules.get(input_id)
        if rule and rule.include:
            formatted_inputs[input_id] = context_manager.format_context(
                context, rule, config.format_specifications.get(input_id)
            )
        elif not rule or rule.include:
            formatted_inputs[input_id] = context
    # Replace placeholders in template
    for input_id, content in formatted_inputs.items():
        placeholder = f"{{{input_id}}}"
        if placeholder in template:
            template = template.replace(placeholder, str(content))
    # Add tool preamble if tools are available
    tools = None
    if config.tools:
        tools = [tool.model_dump() for tool in config.tools]
    else:
        tools = tool_service.list_tools_with_schemas() if tool_service else []
    preamble = build_tool_preamble(tools) if tools else ""
    # Adapt prompt for workflow context (e.g., require JSON output)
    if workflow_context and getattr(workflow_context, "require_json_output", False):
        # Insert a strict JSON instruction at the top
        json_instruction = "Respond ONLY with a JSON object."
        prompt_with_preamble = json_instruction + "\n" + preamble + template
    else:
        prompt_with_preamble = preamble + template
    # Validate total token count
    try:
        total_tokens = TokenCounter.count_tokens(
            prompt_with_preamble, llm_config.model, llm_config.provider
        )
        # Only check token limits if max_context_tokens is set
        if (
            llm_config.max_context_tokens is not None
            and total_tokens > llm_config.max_context_tokens
        ):
            # Truncate prompt if needed
            prompt_with_preamble = prompt_with_preamble[
                : llm_config.max_context_tokens * 4
            ]  # rough estimate
    except ValueError:
        pass
    return prompt_with_preamble


def prepare_messages(config, context: Optional[dict] = None) -> list[dict]:
    """Prepare messages for the API call based on config and context."""
    messages = []
    context = context or {}
    if getattr(config, "templates", None) and "system" in config.templates:
        try:
            system_content = config.templates["system"].format(**context)
            messages.append({"role": "system", "content": system_content})
        except KeyError as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Missing context key for system message: {e}")
    try:
        user_content = config.prompt.format(**context)
        messages.append({"role": "user", "content": user_content})
    except KeyError as e:
        raise ValueError(f"Missing required context key: {e}")
    return messages


def build_messages(config, inputs: dict, context: dict) -> list[dict]:
    """Build message list for API call based on config, inputs, and context."""
    messages = []
    system_template = (
        config.templates.get("system") if getattr(config, "templates", None) else None
    )
    if system_template:
        messages.append(
            {"role": "system", "content": system_template.format(**context)}
        )
    user_template = (
        config.templates.get("user") if getattr(config, "templates", None) else None
    )
    if user_template:
        messages.append({"role": "user", "content": user_template.format(**inputs)})
    else:
        messages.append({"role": "user", "content": config.prompt.format(**inputs)})
    return messages


def truncate_prompt(prompt: str, current_tokens: int, max_tokens: int = 4096) -> str:
    """Truncate prompt to fit within token limit, preserving complete sentences."""
    if current_tokens <= max_tokens:
        return prompt
    tokens_to_remove = current_tokens - max_tokens
    chars_to_remove = tokens_to_remove * 4
    truncated = prompt[:-chars_to_remove]
    last_period = truncated.rfind(".")
    if last_period > 0:
        truncated = truncated[: last_period + 1]
    return truncated


def truncate_messages(
    messages: list[dict], current_tokens: int, max_tokens: int
) -> list[dict]:
    """Truncate messages to fit token limit by removing oldest messages first."""
    from ice_sdk.utils.token_counter import TokenCounter

    if current_tokens <= max_tokens:
        return messages
    messages = messages.copy()
    while current_tokens > max_tokens and len(messages) > 1:
        removed = messages.pop(0)
        try:
            removed_tokens = TokenCounter.count_tokens(
                removed["content"], None, None  # model  # provider
            )
            current_tokens -= removed_tokens
        except Exception:
            current_tokens -= len(removed["content"]) // 4
    return messages
