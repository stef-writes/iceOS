from abc import ABC, abstractmethod
from typing import Dict

from ice_sdk.skills.base import SkillBase
from ice_sdk.utils.coercion import schema_match
from tests.conftest import model_json_schema


class BaseSkill(ABC):
    @abstractmethod
    def execute(self, context: dict) -> dict:
        pass

    @classmethod
    def get_input_schema(cls) -> dict:
        """Get JSON schema for skill inputs.

        Example:
            WebSearchSkill.get_input_schema() => {'type': 'object', ...}
        """
        return model_json_schema(
            cls.InputModel
        )  # From git status, InputModel exists in skills

    @classmethod
    def get_output_schema(cls) -> dict:
        """Get JSON schema for skill outputs.

        Example:
            WebSearchSkill.get_output_schema() => {'type': 'object', ...}
        """
        return model_json_schema(cls.OutputModel)


class ContextTypeManager:
    def __init__(self):
        self._registry: Dict[str, dict] = {}

    def register_context_key(self, key: str, schema: dict) -> None:
        """Register a context key with its JSON Schema type definition.

        Args:
            key: Context key name (e.g. 'web_results')
            schema: JSON Schema dict for values stored under this key
        """
        if key in self._registry:
            raise ValueError(f"Context key {key} already registered")
        self._registry[key] = schema

    def get_compatible_keys(self, target_schema: dict) -> list[str]:
        """Find context keys whose schema matches the target requirements.

        Args:
            target_schema: JSON Schema that input requires

        Returns:
            List of context keys that can fulfill the schema
        """
        return [
            key
            for key, schema in self._registry.items()
            if schema_match(schema, target_schema)  # From coercion utils
        ]


# Singleton instance
context_type_manager = ContextTypeManager()


def test_skill_metadata_schema():
    schema = SkillBase.json_schema()
    assert "properties" in schema
    assert "name" in schema["properties"]
