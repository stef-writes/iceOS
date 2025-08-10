"""Generate Python code snippets for nodes that require implementation.

This module provides utilities for generating clean, typed Python code
for tool and code nodes based on their descriptions.
"""

from __future__ import annotations

import re
from typing import List


class CodeSnippetGenerator:
    """Generates Python code snippets for nodes."""

    # Common code templates
    TEMPLATES = {
        "csv_reader": '''def read_csv_file(file_path: str, **kwargs) -> pd.DataFrame:
    """Read CSV file and return as DataFrame.
    
    Args:
        file_path: Path to the CSV file.
        **kwargs: Additional pandas read_csv arguments.
        
    Returns:
        Loaded DataFrame.
    """
    import pandas as pd
    return pd.read_csv(file_path, **kwargs)''',
        "json_processor": '''def process_json_data(data: dict, key_path: str) -> any:
    """Extract value from nested JSON using dot notation.
    
    Args:
        data: JSON data as dictionary.
        key_path: Dot-separated path (e.g., "user.profile.name").
        
    Returns:
        Extracted value or None if not found.
    """
    keys = key_path.split(".")
    result = data
    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return None
    return result''',
        "api_caller": '''async def call_api(url: str, method: str = "GET", **kwargs) -> dict:
    """Make HTTP API call and return JSON response.
    
    Args:
        url: API endpoint URL.
        method: HTTP method (GET, POST, etc.).
        **kwargs: Additional arguments for requests.
        
    Returns:
        JSON response as dictionary.
    """
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()''',
        "data_transformer": '''def transform_data(data: List[dict], transformations: dict) -> List[dict]:
    """Apply transformations to list of records.
    
    Args:
        data: List of dictionaries to transform.
        transformations: Mapping of field names to transformation functions.
        
    Returns:
        Transformed data.
    """
    result = []
    for record in data:
        transformed = record.copy()
        for field, transform_fn in transformations.items():
            if field in transformed:
                transformed[field] = transform_fn(transformed[field])
        result.append(transformed)
    return result''',
    }

    def generate(self, node_id: str, description: str, node_type: str) -> str:
        """Generate code snippet for a node.

        Args:
            node_id: Unique node identifier.
            description: Natural language description of what the node does.
            node_type: Type of node (tool, code, etc.).

        Returns:
            Generated Python code snippet.
        """
        # Check if we have a template that matches
        for template_key, template_code in self.TEMPLATES.items():
            if template_key in description.lower():
                return self._customize_template(template_code, node_id, description)

        # Generate custom code based on description
        return self._generate_custom_code(node_id, description, node_type)

    def _customize_template(self, template: str, node_id: str, description: str) -> str:
        """Customize a template with node-specific details."""
        # Add node ID as comment
        header = f"# Node: {node_id}\n# Description: {description}\n\n"
        return header + template

    def _generate_custom_code(
        self, node_id: str, description: str, node_type: str
    ) -> str:
        """Generate custom code based on description analysis."""

        # Generate function signature
        func_name = self._generate_function_name(node_id)
        params = self._infer_parameters(description)
        return_type = self._infer_return_type(description)

        # Build code
        code_lines = [
            f"# Node: {node_id}",
            f"# Description: {description}",
            "",
            f"def {func_name}({params}) -> {return_type}:",
            f'    """Auto-generated function for: {description}',
            "    ",
            "    Args:",
        ]

        # Add parameter docs
        for param in self._parse_parameters(params):
            code_lines.append(f"        {param}: TODO - add description")

        code_lines.extend(
            [
                "    ",
                "    Returns:",
                f"        {return_type} result",
                '    """',
                "    # TODO: Implement based on description",
                "    raise NotImplementedError(",
                f'        "Implementation needed for: {description}"',
                "    )",
            ]
        )

        return "\n".join(code_lines)

    def _extract_operations(self, description: str) -> List[str]:
        """Extract operation keywords from description."""
        operation_verbs = [
            "read",
            "write",
            "process",
            "transform",
            "filter",
            "aggregate",
            "calculate",
            "generate",
            "create",
            "update",
            "delete",
            "send",
            "fetch",
            "parse",
            "validate",
            "convert",
            "merge",
            "split",
        ]

        operations = []
        desc_lower = description.lower()
        for verb in operation_verbs:
            if verb in desc_lower:
                operations.append(verb)

        return operations

    def _generate_function_name(self, node_id: str) -> str:
        """Generate a valid Python function name from node ID."""
        # Remove trailing numbers and clean up
        base_name = re.sub(r"_\d+$", "", node_id)
        return base_name.lower()

    def _infer_parameters(self, description: str) -> str:
        """Infer function parameters from description."""
        params = []

        # Check for common input types
        if "file" in description.lower() or "path" in description.lower():
            params.append("file_path: str")
        elif "data" in description.lower():
            params.append("data: Any")
        elif "text" in description.lower() or "string" in description.lower():
            params.append("text: str")
        elif "url" in description.lower():
            params.append("url: str")
        else:
            params.append("input_data: Any")

        # Add options parameter
        params.append("**kwargs")

        return ", ".join(params)

    def _infer_return_type(self, description: str) -> str:
        """Infer return type from description."""
        desc_lower = description.lower()

        if "dataframe" in desc_lower or "csv" in desc_lower:
            return "pd.DataFrame"
        elif "json" in desc_lower or "dict" in desc_lower:
            return "Dict[str, Any]"
        elif "list" in desc_lower or "array" in desc_lower:
            return "List[Any]"
        elif "text" in desc_lower or "string" in desc_lower:
            return "str"
        elif "number" in desc_lower or "count" in desc_lower:
            return "int"
        elif "boolean" in desc_lower or "check" in desc_lower:
            return "bool"
        else:
            return "Any"

    def _parse_parameters(self, params_str: str) -> List[str]:
        """Parse parameter names from parameter string."""
        params = []
        for param in params_str.split(","):
            param = param.strip()
            if ":" in param and param != "**kwargs":
                param_name = param.split(":")[0].strip()
                params.append(param_name)
        return params
