from pydantic import BaseModel
from ice_sdk.utils.cost import track_cost

class LLMOperatorConfig(BaseModel):
    model: str = "gpt-4-1106-preview"
    max_tokens: int = 2000
    temperature: float = 0.7

class LLMOperator(Processor):  # Inherits validation
    """Base LLM interaction unit"""
    config: LLMOperatorConfig
    
    @track_cost(category="llm_operator")
    async def generate(self, prompt: str) -> str:
        return await self.llm_service.generate(
            prompt=prompt,
            model=self.config.model,
            max_tokens=self.config.max_tokens
        ) 