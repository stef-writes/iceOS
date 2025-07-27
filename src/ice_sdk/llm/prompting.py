from typing import Type, Any

def build_robust_prompt(base_prompt: str, output_format: Type[Any]) -> str:
    format_instructions = {
        int: "Respond with ONLY the numeric result, no explanation or formatting.",
        float: "Respond with ONLY the decimal number, no text or symbols.",
        str: "Respond with ONLY the text result, no markdown or formatting.",
        bool: "Respond with ONLY 'true' or 'false' in lowercase.",
    }
    return f"{base_prompt}\n\n{format_instructions[output_format]}"
