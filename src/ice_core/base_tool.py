"""Base tool implementation."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict

class ToolBase(BaseModel, ABC):
    """Base class for all tool implementations.
    
    Tools are stateless, idempotent operations that may have side effects.
    They expose their capabilities through schemas and a standard execute method.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    # Required attributes - must be set by subclasses
    name: str = ""
    description: str = ""
    
    @abstractmethod
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Override in subclasses to provide tool-specific logic."""
        pass
    
    async def execute(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the tool with given inputs.
        
        Subclasses should override _execute_impl.
        """
        
        try:
            # Validate inputs
            self._validate_inputs(kwargs)
            
            # Execute implementation
            result = await self._execute_impl(**kwargs)
            
            # Validate outputs
            self._validate_outputs(result)
            
            return result
            
        except Exception as e:
            # Tools should handle their own errors appropriately
            raise
    
    def _validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate inputs against schema. Override for custom validation."""
        pass
    
    def _validate_outputs(self, outputs: Dict[str, Any]) -> None:
        """Validate outputs against schema. Override for custom validation."""
        pass
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool inputs."""
        # Default implementation uses Pydantic schema
        return cls.model_json_schema()
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool outputs."""
        # Default schema - tools should override with specific output schema
        return {
            "type": "object",
            "properties": {
                "result": {}  # Empty schema means "any value" in JSON Schema
            }
        } 