"""
Purpose: Unified interface to all iceOS memory types with cognitive-specific helpers
Layer: Cognitive/Memory
Dependencies: ice_orchestrator.memory.unified, query optimization
"""

# LEVERAGE iceOS:
# - Use UnifiedMemory from ice_orchestrator.memory.unified for all memory ops
# - Working memory (TTL < 30min) for conversation state & partial blueprints
# - Episodic memory (Redis-backed) for past user sessions & interaction history
# - Semantic memory (SQLite/Vector) for tool relationships & domain knowledge
# - Procedural memory for learned workflow patterns & optimization rules
#
# Key integration points:
# - memory.working.store("conversation:current", dialogue_state)
# - memory.episodic.search("similar_goals", limit=5) for pattern matching
# - memory.semantic.retrieve("tool:compatibility:csv_reader") for planning
# - memory.procedural.search("cost_optimization_rules") for refinement 