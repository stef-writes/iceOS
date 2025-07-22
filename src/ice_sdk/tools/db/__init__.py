from .explain_plan_skill import ExplainPlanSkill
from .index_advisor_skill import IndexAdvisorSkill
from .schema_validator_skill import SchemaValidatorSkill

try:
    from ice_sdk.registry.tool import global_tool_registry

    global_tool_registry.register("index_advisor", IndexAdvisorSkill())
    global_tool_registry.register("explain_plan", ExplainPlanSkill())
    global_tool_registry.register("schema_validator", SchemaValidatorSkill())
except Exception:  # pragma: no cover
    pass
