"""Core node implementation with strong typing."""

from typing import Any, Dict

from ice_sdk.core.validation import InvalidNodeConfig
from ice_sdk.models.node_models import NodeConfig
from ice_sdk.registry import SkillRegistry
from ice_sdk.utils.type_system import TypeSystem


class StronglyTypedNode(NodeConfig):
    def validate(self) -> None:
        # Validate input/output schemas against registered skills/LLMs
        if self.type == "skill":
            skill = SkillRegistry.get(self.tool_name)
            if not skill.validate_input_schema(self.input_schema):
                raise InvalidNodeConfig(...)
        # Similar checks for LLM nodes

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Automatic type conversion and validation
        cleaned_inputs = TypeSystem.clean_inputs(self, context)
        raw_output = super().execute(cleaned_inputs)
        return TypeSystem.clean_outputs(self, raw_output)
