"""
Purpose: Transform validated intent fragments into PartialBlueprint objects
Layer: Blueprint
Dependencies: ice_core.models.mcp, cognitive.decomposer
"""

# LEVERAGE iceOS:
# - Use ice_core.models.mcp.PartialBlueprint for incremental construction
# - Use ice_core.models.mcp.PartialNodeSpec for nodes with pending connections
# - Key features:
#   * Relaxed validation during construction
#   * AI suggestions for next nodes via next_suggestions field
#   * Incremental validation with clear error messages
#   * Conversion to executable Blueprint when complete
#
# Integration example:
# partial = PartialBlueprint()
# partial.add_node(PartialNodeSpec(
#     id="reader", 
#     type="tool",
#     tool_name="csv_reader",
#     pending_outputs=["data"]  # Not yet connected
# ))
# partial._validate_incremental()  # Updates validation_errors & suggestions
# if partial.is_complete:
#     blueprint = partial.to_blueprint()  # Ready for MCP validation 