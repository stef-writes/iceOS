# This file provides single-step tool call detection and formatting utilities only.
import json
from typing import Any, Optional, Tuple


def detect_tool_call(response: str) -> Tuple[Optional[str], Optional[Any]]:
    """
    Detect and parse a tool/function call from an LLM response.
    Returns (tool_name, tool_args) if found, else (None, None).
    Handles OpenAI/Anthropic style and JSON with 'function_call'.
    """
    if not response:
        return None, None
    try:
        parsed = json.loads(response)
        if "function_call" in parsed:
            call = parsed["function_call"]
            tool_name = call.get("name")
            tool_args = call.get("arguments")
            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except Exception:
                    pass
            return tool_name, tool_args
    except Exception:
        if response.strip().startswith('{"function_call"'):
            try:
                parsed = json.loads(response.strip())
                call = parsed["function_call"]
                tool_name = call.get("name")
                tool_args = call.get("arguments")
                if isinstance(tool_args, str):
                    tool_args = json.loads(tool_args)
                return tool_name, tool_args
            except Exception:
                return None, None
    return None, None


def format_tool_output(tool_name: str, output: dict) -> str:
    """
    Format tool output for inclusion in the prompt (always as JSON).
    """
    return f"Tool '{tool_name}' output: {json.dumps(output)}"
