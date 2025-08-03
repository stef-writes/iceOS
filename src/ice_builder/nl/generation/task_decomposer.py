"""Decompose high-level plans into executable task specifications.

This module breaks down abstract plans into concrete steps that can be
mapped to specific iceOS node types and configurations.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, TypedDict


class _StepInfo(TypedDict):
    step: int
    type: str
    description: str
    dependency_steps: List[int]


class TaskDecomposer:
    """Decomposes high-level plans into structured task specifications."""
    
    # Pattern to parse plan steps
    STEP_PATTERN = re.compile(
        r"STEP\s+(\d+):\s*\[(\w+)\]\s*(.+?)(?:DEPENDS ON:\s*(.+?))?$",
        re.MULTILINE | re.IGNORECASE
    )
    
    def decompose(self, plan: str) -> List[Dict[str, Any]]:
        """Decompose a structured plan into task specifications.
        
        Args:
            plan: Structured plan text with steps and dependencies.
            
        Returns:
            List of task dictionaries with id, type, description, and dependencies.
        """
        tasks = []
        
        # First pass: extract all steps
        step_map: Dict[int, _StepInfo] = {}
        for match in self.STEP_PATTERN.finditer(plan):
            step_num = int(match.group(1))
            node_type = match.group(2).lower()
            description = match.group(3).strip()
            deps_str = match.group(4)
            
            # Parse dependencies
            dependency_steps: List[int] = []
            if deps_str and deps_str.strip().lower() != "none":
                dep_nums = re.findall(r"\d+", deps_str)
                dependency_steps = [int(num) for num in dep_nums]
            
            step_map[step_num] = {
                "step": step_num,
                "type": node_type,
                "description": description,
                "dependency_steps": dependency_steps,
            }
        
        # Second pass: convert to node specifications
        for step_num in sorted(step_map.keys()):
            step_data = step_map[step_num]
            
            # Generate node ID from description
            node_id = self._generate_node_id(str(step_data["description"]), step_num)
            
            # Map dependency step numbers to node IDs
            dependencies = [
                self._generate_node_id(str(step_map[dep]["description"]), dep)
                for dep in step_data["dependency_steps"]
                if dep in step_map
            ]
            
            # Extract configuration hints from description
            config = self._extract_config(step_data["type"], step_data["description"])
            
            tasks.append({
                "id": node_id,
                "type": step_data["type"],
                "description": step_data["description"],
                "config": config,
                "dependencies": dependencies,
            })
        
        return tasks
    
    def _generate_node_id(self, description: str, step_num: int) -> str:
        """Generate a valid node ID from description."""
        # Extract key words
        words = re.findall(r"\w+", description.lower())
        
        # Filter out common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        key_words = [w for w in words if w not in stop_words][:3]
        
        if key_words:
            base_id = "_".join(key_words)
        else:
            base_id = f"step_{step_num}"
        
        # Ensure valid identifier
        base_id = re.sub(r"[^a-z0-9_]", "_", base_id)
        return f"{base_id}_{step_num}"
    
    def _extract_config(self, node_type: str, description: str) -> Dict[str, Any]:  # type: ignore[override]
        """Extract configuration parameters from description."""
        config = {}
        
        # Extract quoted strings as potential prompts or messages
        quoted = re.findall(r'"([^"]+)"', description)
        if quoted:
            if node_type == "llm":
                config["prompt"] = quoted[0]
            elif node_type == "human":
                config["prompt"] = quoted[0]
        
        # Extract tool names
        if node_type == "tool":
            # Look for common tool patterns
            if "csv" in description.lower():
                config["tool_name"] = "csv_reader"
            elif "api" in description.lower():
                config["tool_name"] = "api_caller"
            elif "email" in description.lower():
                config["tool_name"] = "email_sender"
            else:
                # Extract first verb as potential tool name
                verbs = re.findall(r"\b(read|write|process|analyze|generate|create|send|fetch)\b", 
                                  description.lower())
                if verbs:
                    config["tool_name"] = verbs[0]
        
        # Extract model hints for LLM nodes
        if node_type == "llm":
            if "gpt" in description.lower():
                config["model"] = "gpt-4o-mini"
                config["provider"] = "openai"
            elif "claude" in description.lower():
                config["model"] = "claude-3-haiku-20240307"
                config["provider"] = "anthropic"
            elif "deepseek" in description.lower():
                config["model"] = "deepseek-r1"
                config["provider"] = "deepseek"
        
        # Extract iteration conditions for loops
        if node_type == "loop":
            # Look for "until" or "while" conditions
            until_match = re.search(r"until\s+(.+)", description, re.IGNORECASE)
            if until_match:
                config["exit_condition"] = until_match.group(1).strip()
            
            # Look for max iterations
            max_match = re.search(r"(\d+)\s*(?:times|iterations)", description)
            if max_match:
                config["max_iterations"] = int(max_match.group(1))
        
        return config