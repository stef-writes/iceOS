"""Pure LLM node - no tools, just inference."""
from typing import Dict, Any, Optional
from ice_core.models import BaseNode
from ice_sdk.providers.llm_service import LLMService
from ice_core.models import LLMConfig, ModelProvider

class LLMNode(BaseNode):
    """Pure LLM inference node."""
    
    model: str
    prompt_template: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None
    provider: str = "openai"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Schema for inputs."""
        return {
            "type": "object",
            "additionalProperties": True  # Accept any inputs for template
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """Schema for outputs."""
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "usage": {"type": "object"}
            },
            "required": ["text"]
        }
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Call LLM with rendered prompt."""
        # Render prompt template
        prompt = self.prompt_template.format(**inputs)
        
        # Create LLM config
        llm_config = LLMConfig(
            provider=self.provider,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        # Call LLM service
        service = LLMService()
        text, usage, error = await service.generate(
            llm_config=llm_config,
            prompt=prompt
        )
        
        if error:
            raise Exception(f"LLM error: {error}")
        
        return {
            "text": text,
            "usage": usage or {}
        } 