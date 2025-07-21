from .explain_plan_skill import ExplainPlanSkill
from .index_advisor_skill import IndexAdvisorSkill
from .schema_validator_skill import SchemaValidatorSkill

try:
    from ..registry import global_skill_registry

    global_skill_registry.register("index_advisor", IndexAdvisorSkill())
    global_skill_registry.register("explain_plan", ExplainPlanSkill())
    global_skill_registry.register("schema_validator", SchemaValidatorSkill())
except Exception:  # pragma: no cover
    pass
