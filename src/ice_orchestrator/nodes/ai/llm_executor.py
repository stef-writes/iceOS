import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ice_sdk.models.config import LLMConfig
from ice_sdk.models.node_models import (
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
    UsageMetadata,
)
from ice_orchestrator.nodes.ai.output_validator import OutputValidator
from ice_orchestrator.nodes.ai.tool_call_utils import detect_tool_call
from ice_orchestrator.nodes.utils.error_handling import OpenAIErrorHandler
from ice_orchestrator.nodes.utils.prompt_builder import prepare_prompt
from ice_sdk.utils.type_coercion import coerce_types

logger = logging.getLogger(__name__)


def get_system_prompt(output_format: str) -> Optional[str]:
    if output_format == "json":
        return 'Respond ONLY with a JSON object: {"tweet": "<your tweet here>"}'
    elif output_format == "function_call":
        return "If you want to use a tool, respond with a function_call JSON as shown in the examples below."
    elif output_format == "plain":
        return "Respond with a short answer in plain English."
    return None


async def llm_execute(
    config: NodeConfig,
    context_manager,
    llm_config: LLMConfig,
    llm_service,
    tool_service,
    context: Optional[Dict[str, Any]] = None,
    max_steps: int = 5,
    workflow_context=None,
) -> NodeExecutionResult:
    """
    Orchestrate LLM execution, tool call detection, tool execution, and output validation.
    Returns a NodeExecutionResult.
    """
    start_time = datetime.utcnow()
    usage_metadata = None
    context = context or {}
    output_format = getattr(config, "output_format", "plain")
    system_prompt = get_system_prompt(output_format)
    error_message_prefix = f"Node '{config.id}' (Name: '{config.name}', Provider: {llm_config.provider}, Model: {llm_config.model}): "
    try:
        try:
            prompt_template_for_handler = await prepare_prompt(
                config, context_manager, llm_config, tool_service, context
            )
            if system_prompt:
                prompt_template_for_handler = (
                    system_prompt + "\n" + prompt_template_for_handler
                )
        except KeyError as e:
            logger.error(
                f"{error_message_prefix}Missing key '{str(e)}' for prompt template. Context: {json.dumps(context, indent=2, default=str)}",
                exc_info=True,
            )
            return NodeExecutionResult(
                success=False,
                error=f"{error_message_prefix}Prompt formatting error: Missing key '{str(e)}'.",
                metadata=NodeMetadata(
                    node_id=config.id,
                    node_type=getattr(config, "type", "unknown"),
                    name=getattr(config, "name", None),
                    provider=getattr(config, "provider", None),
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    error_type="PromptFormattingError",
                ),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )
        tools = [tool.model_dump() for tool in config.tools] if config.tools else None
        generated_text, usage_dict, handler_error = await llm_service.generate(
            llm_config,
            prompt_template_for_handler,
            context=context,
            tools=tools,
            timeout_seconds=(
                getattr(config, "timeout_seconds", None)
                or getattr(config, "timeout", None)
                or 30
            ),
            max_retries=getattr(config, "max_retries", 2),
        )
        logger.info(f"{error_message_prefix}Raw LLM output: {repr(generated_text)}")
        tool_name, tool_args = detect_tool_call(generated_text)
        tool_call_detected = tool_name is not None
        if tool_call_detected:
            logger.info(
                f"Tool/function call detected: {tool_name} with args: {tool_args}"
            )

            # Merge args from config with args from LLM
            final_tool_args = config.tool_args.copy() if config.tool_args else {}
            if tool_args:
                final_tool_args.update(tool_args)

            tool_exec_result = await tool_service.execute(
                tool_name, final_tool_args or {}
            )
            if not tool_exec_result["success"]:
                tool_error = tool_exec_result["error"]
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                return NodeExecutionResult(
                    success=False,
                    output=None,
                    error=f"{error_message_prefix}{tool_error}" if tool_error else None,
                    metadata=NodeMetadata(
                        node_id=config.id,
                        node_type=getattr(config, "type", "unknown"),
                        name=getattr(config, "name", None),
                        provider=getattr(config, "provider", None),
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        error_type="ToolExecutionError",
                    ),
                    usage=usage_metadata,
                    execution_time=duration,
                )
            try:
                output_data = coerce_types(
                    tool_exec_result["output"], config.output_schema
                )
                validation_success = True
                validation_error = None
            except Exception as e:
                output_data = None
                validation_success = False
                validation_error = str(e)
            final_success = validation_success
            final_error = validation_error if not validation_success else None
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            if usage_dict:
                usage_metadata = UsageMetadata(
                    prompt_tokens=usage_dict.get("prompt_tokens", 0),
                    completion_tokens=usage_dict.get("completion_tokens", 0),
                    total_tokens=usage_dict.get("total_tokens", 0),
                    model=llm_config.model,
                    node_id=config.id,
                    provider=llm_config.provider,
                )
            return NodeExecutionResult(
                success=final_success,
                output=output_data,
                error=f"{error_message_prefix}{final_error}" if final_error else None,
                metadata=NodeMetadata(
                    node_id=config.id,
                    node_type=getattr(config, "type", "unknown"),
                    name=getattr(config, "name", None),
                    provider=getattr(config, "provider", None),
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    error_type=(
                        "SchemaValidationError"
                        if (not final_success and validation_error)
                        else None
                    ),
                ),
                usage=usage_metadata,
                execution_time=duration,
            )
        # Output parsing/validation logic
        output_data, validation_success, validation_error = (
            OutputValidator.validate_and_coerce(
                generated_text, output_format, config.output_schema
            )
        )

        final_success = validation_success
        final_error = validation_error

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        if usage_dict:
            usage_metadata = UsageMetadata(
                prompt_tokens=usage_dict.get("prompt_tokens", 0),
                completion_tokens=usage_dict.get("completion_tokens", 0),
                total_tokens=usage_dict.get("total_tokens", 0),
                model=llm_config.model,
                node_id=config.id,
                provider=llm_config.provider,
            )
        return NodeExecutionResult(
            success=final_success,
            output=output_data,
            error=f"{error_message_prefix}{final_error}" if final_error else None,
            metadata=NodeMetadata(
                node_id=config.id,
                node_type=getattr(config, "type", "unknown"),
                name=getattr(config, "name", None),
                provider=getattr(config, "provider", None),
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_type=(
                    "SchemaValidationError"
                    if (not final_success and final_error)
                    else None
                ),
            ),
            usage=usage_metadata,
            execution_time=duration,
        )
    except Exception as e:
        logger.error(
            f"{error_message_prefix}Unexpected error in execute method: {str(e)}",
            exc_info=True,
        )
        return NodeExecutionResult(
            success=False,
            error=f"{error_message_prefix}{OpenAIErrorHandler.format_error_message(e)}",
            metadata=NodeMetadata(
                node_id=config.id,
                node_type=getattr(config, "type", "unknown"),
                name=getattr(config, "name", None),
                provider=getattr(config, "provider", None),
                start_time=start_time,
                end_time=datetime.utcnow(),
                error_type=e.__class__.__name__,
            ),
            execution_time=(datetime.utcnow() - start_time).total_seconds(),
        )
