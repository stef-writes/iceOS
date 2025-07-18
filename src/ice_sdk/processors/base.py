from pydantic import BaseModel
from ice_sdk.utils.deprecation import deprecated

class ProcessorConfig(BaseModel):
    input_schema: dict
    output_schema: dict
    timeout: int = 30

@deprecated("0.4.0", "Use Processor instead")
class Node:
    pass

class Processor(Node):
    """Base data transformation unit"""
    config: ProcessorConfig
    
    def validate(self) -> bool:
        return validate_schemas(
            self.config.input_schema, 
            self.config.output_schema
        )
    
    async def process(self, data: dict) -> dict:
        raise NotImplementedError 