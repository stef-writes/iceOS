from typing import Any, Dict, Mapping

from ice_sdk.utils.coercion import schema_match  # From untracked files

class ContextTypeManager:
    def __init__(self):
        self._registry: Dict[str, Mapping[str, Any]] = {}

    def register_context_key(self, key: str, schema: Mapping[str, Any]) -> None:
        """Register a context key with its JSON Schema type definition.

        Args:
            key: Context key name (e.g. 'web_results')
            schema: JSON Schema dict for values stored under this key
        """
        if key in self._registry:
            raise ValueError(f"Context key {key} already registered")
        self._registry[key] = schema

    def get_compatible_keys(self, target_schema: Mapping[str, Any]) -> list[str]:
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
