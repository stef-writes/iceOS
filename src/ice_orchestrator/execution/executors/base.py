import json
from typing import Any, Dict
from ice_orchestrator.exceptions import InputConversionError
from ice_orchestrator.models import NodeConfig

async def _resolve_inputs(node: NodeConfig) -> dict:
    inputs = {}
    for input_key, mapping in node.input_mappings.items():
        raw_value = await _fetch_mapped_value(mapping)
        
        # Apply conversion if specified
        if "conversion" in mapping:
            try:
                converted = eval(  # Security note: uses isolated env
                    mapping["conversion"],
                    {"__builtins__": None},
                    {"value": raw_value, "json": json}
                )
                inputs[input_key] = converted
            except Exception as e:
                raise InputConversionError(
                    f"Failed conversion for {input_key}: {str(e)}"
                ) from e
        else:
            inputs[input_key] = raw_value
    return inputs