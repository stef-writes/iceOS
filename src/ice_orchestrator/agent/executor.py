"""Agent executor for runtime agent execution in the orchestrator."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import structlog

from ice_core.models import NodeExecutionResult
from ice_sdk.services import ServiceLocator

if TYPE_CHECKING:
    from ice_core.base_tool import ToolBase

logger = structlog.get_logger(__name__)


class AgentExecutor:
    """Executes agent nodes with tool coordination and memory management."""
    
    def __init__(self):
        self.llm_service = ServiceLocator.get("llm_service")
        self.tool_service = ServiceLocator.get("tool_service")
    
    async def execute_agent(
        self,
        agent: Any,  # AgentNode instance
        inputs: Dict[str, Any],
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute an agent's reasoning loop with tools."""
        max_iterations = max_iterations or agent.config.max_retries or 10
        iteration = 0
        
        # Initialize context with inputs
        context = {**inputs}
        
        # Get tools for the agent
        tools = await self._load_tools(agent.config.tools)
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Build prompt with current context
                prompt = self._build_agent_prompt(
                    agent.config.system_prompt,
                    context,
                    tools,
                    iteration
                )
                
                # Get LLM response
                response = await self.llm_service.complete(
                    prompt=prompt,
                    config=agent.config.llm_config
                )
                
                # Parse response for tool calls or final answer
                result = self._parse_agent_response(response)
                
                if result.get("type") == "tool_call":
                    # Execute tool
                    tool_result = await self._execute_tool(
                        result["tool_name"],
                        result["tool_args"],
                        tools
                    )
                    
                    # Update context with tool result
                    context["last_tool_result"] = tool_result
                    context["tool_history"] = context.get("tool_history", [])
                    context["tool_history"].append({
                        "tool": result["tool_name"],
                        "args": result["tool_args"],
                        "result": tool_result
                    })
                    
                elif result.get("type") == "final_answer":
                    # Agent has reached a conclusion
                    return {
                        "status": "success",
                        "response": result["answer"],
                        "iterations": iteration,
                        "tool_history": context.get("tool_history", []),
                        "usage": response.get("usage", {})
                    }
                    
            except Exception as e:
                logger.error("Agent execution error", error=str(e), iteration=iteration)
                if iteration >= max_iterations:
                    return {
                        "status": "error",
                        "error": str(e),
                        "iterations": iteration
                    }
        
        # Max iterations reached
        return {
            "status": "max_iterations_reached",
            "response": "Agent did not reach a conclusion within iteration limit",
            "iterations": iteration,
            "tool_history": context.get("tool_history", [])
        }
    
    async def _load_tools(self, tool_names: List[str]) -> Dict[str, "ToolBase"]:
        """Load tools by name from the tool service."""
        tools = {}
        for name in tool_names:
            tool = await self.tool_service.get_tool(name)
            if tool:
                tools[name] = tool
        return tools
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        available_tools: Dict[str, "ToolBase"]
    ) -> Dict[str, Any]:
        """Execute a tool with given arguments."""
        tool = available_tools.get(tool_name)
        if not tool:
            return {"error": f"Tool {tool_name} not found"}
        
        try:
            result = await tool.execute(tool_args)
            return result
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def _build_agent_prompt(
        self,
        system_prompt: str,
        context: Dict[str, Any],
        tools: Dict[str, "ToolBase"],
        iteration: int
    ) -> str:
        """Build the prompt for the agent including context and available tools."""
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in tools.items()
        ])
        
        prompt = f"""{system_prompt}

Available Tools:
{tool_descriptions}

Current Context:
{context}

Iteration: {iteration}

Please analyze the context and either:
1. Call a tool to gather more information (respond with JSON: {{"type": "tool_call", "tool_name": "...", "tool_args": {{...}}}})
2. Provide a final answer (respond with JSON: {{"type": "final_answer", "answer": "..."}})
"""
        return prompt
    
    def _parse_agent_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the agent's response to extract tool calls or final answer."""
        from .utils import extract_json
        
        text = response.get("text", "")
        
        # Try to extract JSON from response
        json_data = extract_json(text)
        if json_data:
            return json_data
        
        # Fallback: treat as final answer if no valid JSON
        return {
            "type": "final_answer",
            "answer": text
        } 