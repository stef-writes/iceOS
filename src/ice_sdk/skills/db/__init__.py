from .explain_plan_skill import ExplainPlanSkill  # noqa: F401
from .index_advisor_skill import IndexAdvisorSkill  # noqa: F401
from .schema_validator_skill import SchemaValidatorSkill  # noqa: F401

try:
    from ..registry import global_skill_registry

    global_skill_registry.register("index_advisor", IndexAdvisorSkill())
    global_skill_registry.register("explain_plan", ExplainPlanSkill())
    global_skill_registry.register("schema_validator", SchemaValidatorSkill())
except Exception:  # pragma: no cover
    pass
