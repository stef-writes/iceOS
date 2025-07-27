from .explain_plan_tool import ExplainPlanTool
from ice_core.models import NodeType
from .index_advisor_tool import IndexAdvisorTool
from .schema_validator_tool import SchemaValidatorTool

try:
    from ice_core.unified_registry import registry

    registry.register_instance(NodeType.TOOL, "index_advisor", IndexAdvisorTool())
    registry.register_instance(NodeType.TOOL, "explain_plan", ExplainPlanTool())
    registry.register_instance(NodeType.TOOL, "schema_validator", SchemaValidatorTool())
except Exception:  # pragma: no cover
    pass
