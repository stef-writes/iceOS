"""
Purpose: Coordinate all cognitive subsystems in the POI (Plan-Observe-Iterate) loop
Layer: Cognitive
Dependencies: All cognitive modules, state machine, async coordination
"""

# FROSTY <-> iceOS INTEGRATION OVERVIEW:
#
# 1. MEMORY SYSTEM (ice_orchestrator.memory.unified.UnifiedMemory)
#    - Working: Active conversation, partial blueprints (TTL-managed)
#    - Episodic: User interaction history, past sessions (Redis-backed)
#    - Semantic: Tool relationships, domain knowledge (Vector/SQLite)
#    - Procedural: Learned patterns, optimization rules (File-backed)
#
# 2. BLUEPRINT CONSTRUCTION (ice_core.models.mcp)
#    - PartialBlueprint: Incremental construction with relaxed validation
#    - PartialNodeSpec: Nodes with pending connections
#    - MCP API validation: Schema, budget, policy checks
#    - Progressive refinement: Build -> Validate -> Fix -> Repeat
#
# 3. GRAPH INTELLIGENCE (NetworkX + ice_orchestrator.context.graph_analyzer)
#    - Dependency analysis: Topological sorting, level assignment
#    - Optimization insights: Critical path, bottlenecks, parallelization
#    - Pattern matching: Find similar subgraphs in workflow history
#    - Execution estimation: Time/cost prediction based on graph structure
#
# 4. TOOL ECOSYSTEM (ice_core.unified_registry + ice_sdk.tools)
#    - Dynamic tool discovery: Registry queries by capability
#    - Tool generation: Follow ToolBase patterns, auto-register
#    - Category organization: core/ai/system/web/db/domain
#    - Schema validation: Input/output compatibility checks
#
# 5. EXECUTION CONTEXT (ice_orchestrator.workflow.Workflow)
#    - DAG execution: Parallel node execution, retry logic
#    - Cost tracking: Token usage, API calls, execution time
#    - Event streaming: Real-time progress updates
#    - Cache integration: Result reuse for identical inputs
#
# The CognitiveOrchestrator coordinates all these systems to turn
# natural language into validated, optimized, executable workflows. 