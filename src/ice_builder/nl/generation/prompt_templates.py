"""Structured prompt templates for each stage of the blueprint generation pipeline.

These templates guide the LLMs to produce consistent, parseable outputs that
can be transformed into valid iceOS node configurations.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .node_selection_heuristics import describe_node_capabilities


INTENT_EXTRACTION_PROMPT = """You are an expert at understanding user requirements for workflow automation.

Extract the following from the user's request:
1. Primary goal (what they want to achieve)
2. Key constraints or requirements
3. Input data/sources mentioned
4. Expected output/deliverables
5. Any specific tools or services mentioned

User request: {specification}

Respond in JSON format:
{{
    "goal": "primary objective",
    "constraints": ["constraint1", "constraint2"],
    "inputs": ["input1", "input2"],
    "outputs": ["output1", "output2"],
    "tools_mentioned": ["tool1", "tool2"]
}}"""


PLANNING_PROMPT = """You are an expert workflow architect. Create a high-level execution plan.

Context:
- Goal: {goal}
- Constraints: {constraints}
- Inputs: {inputs}
- Outputs: {outputs}
- Available tools: {available_tools}
- Suggested tools for this task: {suggested_tools}

Available node types:
{node_capabilities}

IMPORTANT PRINCIPLES - Keep it simple and atomic:
1. DEFAULT to 'tool' nodes for any I/O operations (read/write files, API calls)
2. Use 'llm' for text generation WITHOUT state (not 'agent')
3. Use 'code' for data transformations and calculations
4. AVOID 'swarm' - it's almost never needed (use 'parallel' + 'llm' instead)
5. AVOID 'agent' unless you specifically need tool access + memory together
6. Be SPECIFIC - "process data" is too vague, say "parse CSV columns A,B,C"

When to use each node type (in order of preference):
- 'tool': ANY pre-built function (csv_reader, api_caller, file_writer) - USE THIS FIRST
- 'llm': Text generation/analysis WITHOUT memory or tools (summaries, classification)
- 'code': Custom calculations, data transforms, format conversions  
- 'condition': Simple if/then branching based on data
- 'loop': Iterating over a list or until condition (with clear exit)
- 'parallel': Multiple INDEPENDENT operations at once
- 'human': Manual review/approval required (blocks execution)
- 'agent': ONLY if you need tools + conversation memory (rare)
- 'workflow': Reusable sub-workflow (avoid nesting)
- 'monitor': Long-running metric watcher (very rare)
- 'swarm': Almost NEVER - requires strong justification

Create a numbered plan where each step specifies:
1. What needs to be done
2. Which node type is most appropriate (from the list above)
3. Dependencies on previous steps

Format each step as:
STEP N: [node_type] Description of what this step does
DEPENDS ON: [comma-separated step numbers or "none"]

EXAMPLE of a GOOD atomic plan:
STEP 1: [tool] Read inventory data from CSV file
DEPENDS ON: none

STEP 2: [code] Calculate reorder quantities based on thresholds
DEPENDS ON: 1

STEP 3: [tool] Call supplier API to check prices
DEPENDS ON: 2

STEP 4: [llm] Generate purchase order summary text
DEPENDS ON: 3

STEP 5: [tool] Save order to output.json
DEPENDS ON: 4

EXAMPLE of a BAD over-engineered plan:
STEP 1: [agent] Intelligent CSV processor agent
STEP 2: [swarm] Multi-agent consensus on reorder strategy
STEP 3: [agent] Smart API negotiation agent

Make the plan comprehensive but SIMPLE. Every step should do ONE concrete thing."""


DECOMPOSITION_PROMPT = """Convert this execution plan into specific node configurations.

Plan:
{plan}

For each step, provide:
1. A unique node ID (snake_case)
2. The exact node type
3. Key configuration parameters
4. Dependencies (node IDs)

Respond in JSON format:
{{
    "nodes": [
        {{
            "id": "node_id",
            "type": "node_type",
            "description": "what it does",
            "config": {{"param": "value"}},
            "dependencies": ["dep1_id", "dep2_id"]
        }}
    ]
}}"""


MERMAID_GENERATION_PROMPT = """Create a Mermaid flowchart diagram for this workflow.

Nodes:
{nodes}

Requirements:
- Use descriptive labels (not just IDs)
- Show all dependencies as arrows
- Group related nodes in subgraphs where appropriate
- Add styling to distinguish node types (use classes)

Example format:
graph TD
    A[Start] --> B[Process Data]
    B --> C{Decision}
    C -->|Yes| D[Action 1]
    C -->|No| E[Action 2]
    
Return ONLY the Mermaid code, no explanations."""


CODE_GENERATION_PROMPT = """Generate Python code implementations for the following nodes.

Nodes requiring code:
{code_nodes}

For each node that needs code:
1. Write clean, typed Python functions
2. Include docstrings with parameter descriptions
3. Handle errors gracefully
4. Use only standard library or these allowed packages: pandas, numpy, requests

Format:
```python
# Node: node_id
def function_name(param1: type1, param2: type2) -> return_type:
    \"\"\"Brief description.
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Description
    \"\"\"
    # Implementation
```"""


def format_intent_prompt(specification: str) -> str:
    """Format the intent extraction prompt with user specification."""
    return INTENT_EXTRACTION_PROMPT.format(specification=specification)


def format_planning_prompt(intent_data: Dict[str, Any]) -> str:
    """Format the planning prompt with extracted intent data."""
    node_caps = "\n".join(
        f"- {node_type}: {desc}"
        for node_type, desc in describe_node_capabilities().items()
    )
    
    return PLANNING_PROMPT.format(
        goal=intent_data["goal"],
        constraints=", ".join(intent_data.get("constraints", [])),
        inputs=", ".join(intent_data.get("inputs", [])),
        outputs=", ".join(intent_data.get("outputs", [])),
        available_tools=", ".join(intent_data.get("available_tools", ["[none registered]"])),
        suggested_tools=", ".join(intent_data.get("suggested_tools", ["[none suggested]"])),
        node_capabilities=node_caps,
    )


def format_decomposition_prompt(plan: str) -> str:
    """Format the decomposition prompt with the execution plan."""
    return DECOMPOSITION_PROMPT.format(plan=plan)


def format_mermaid_prompt(nodes: List[Dict[str, Any]]) -> str:
    """Format the Mermaid generation prompt with node data."""
    nodes_desc = "\n".join(
        f"- {node['id']} ({node['type']}): {node.get('description', 'No description')}"
        for node in nodes
    )
    return MERMAID_GENERATION_PROMPT.format(nodes=nodes_desc)


def format_code_prompt(nodes: List[Dict[str, Any]]) -> str:
    """Format the code generation prompt for nodes requiring code."""
    code_nodes = [
        node for node in nodes
        if node["type"] in ["code", "tool"] and not node.get("code")
    ]
    
    nodes_desc = "\n".join(
        f"- {node['id']}: {node.get('description', 'Generate implementation')}"
        for node in code_nodes
    )
    
    return CODE_GENERATION_PROMPT.format(code_nodes=nodes_desc)