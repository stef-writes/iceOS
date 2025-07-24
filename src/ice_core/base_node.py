"""Base node implementation."""
from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, ConfigDict
from ice_core.protocols.node import INode
from ice_core.models.node_models import NodeExecutionResult
import time

class BaseNode(BaseModel, INode):
    """Base class for all node implementations.
    
    Provides common execution flow, validation, and error handling.
    Subclasses should override _execute_impl with their specific logic.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    async def validate(self) -> None:
        """Validate node configuration.
        
        Default implementation relies on Pydantic validation.
        Override for custom validation logic.
        """
        # Pydantic handles field validation automatically
        pass
    
    async def execute(self, inputs: Dict[str, Any]) -> NodeExecutionResult:
        """Execute the node with common error handling and timing."""
        start_time = time.time()
        
        try:
            # Validate inputs
            self._validate_inputs(inputs)
            
            # Execute implementation
            output = await self._execute_impl(inputs)
            
            # Validate outputs
            self._validate_outputs(output)
            
            return NodeExecutionResult(
                success=True,
                output=output,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return NodeExecutionResult(
                success=False,
                output={},
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses to provide node-specific logic."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _execute_impl"
        )
    
    def _validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate inputs against input schema.
        
        Override to provide custom validation.
        """
        # Subclasses can implement schema validation
        pass
    
    def _validate_outputs(self, outputs: Dict[str, Any]) -> None:
        """Validate outputs against output schema.
        
        Override to provide custom validation.
        """
        # Subclasses can implement schema validation
        pass 