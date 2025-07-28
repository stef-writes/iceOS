"""Code node - direct code execution."""
from typing import Dict, Any, Literal
from ice_core.base_node import BaseNode
import ast

class CodeNode(BaseNode):
    """Execute Python code directly."""
    
    code: str
    runtime: Literal["python"] = "python"
    
    @property

    
    def output_schema(self) -> Dict[str, Any]:

    
        return {
        "type": "object",
        "additionalProperties": True  # Code can return anything
    }
    
    async def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code safely."""
        if self.runtime != "python":
            raise NotImplementedError(f"Runtime '{self.runtime}' not supported yet")
        
        # Validate code is safe (basic check)
        try:
            ast.parse(self.code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python code: {e}")
        
        # Create execution context
        context = {
            "__builtins__": {
                "len": len,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "print": print,
            },
            "inputs": inputs,
            "outputs": {}
        }
        
        # Execute code
        try:
            exec(self.code, context)
            return context.get("outputs", {})
        except Exception as e:
            raise RuntimeError(f"Code execution failed: {e}") 