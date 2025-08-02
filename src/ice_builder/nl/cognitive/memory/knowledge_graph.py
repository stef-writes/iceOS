"""
Purpose: Tool compatibility matrix, pattern library, domain ontologies
Layer: Cognitive/Memory
Dependencies: NetworkX graphs, semantic similarity, graph embeddings
"""

# LEVERAGE iceOS:
# - Use NetworkX (already in iceOS) for tool relationship graphs
# - Build on ice_orchestrator.context.graph_analyzer patterns
# - Store in semantic memory with graph serialization
#
# Knowledge graph structure:
# G = nx.DiGraph()
# 
# Node types:
# - Tools: {id: "csv_reader", type: "tool", category: "core", outputs: ["dataframe"]}
# - Concepts: {id: "dataframe", type: "concept", compatible_with: [...]}
# - Patterns: {id: "etl_pattern", type: "pattern", nodes: ["read", "transform", "write"]}
# - Domains: {id: "finance", type: "domain", common_tools: [...]}
#
# Edge types:
# - "outputs_to": tool -> concept (what it produces)
# - "accepts": tool -> concept (what it can process)
# - "commonly_follows": tool -> tool (workflow patterns)
# - "belongs_to": tool -> domain
#
# Queries:
# - nx.shortest_path(G, current_output_type, desired_output_type)
# - nx.descendants(G, tool_id) # What can this tool connect to?
# - Pattern matching via subgraph isomorphism 