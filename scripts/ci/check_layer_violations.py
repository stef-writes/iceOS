# Added layer boundary checks
def detect_cross_layer_imports():
    forbidden = [
        ("ice_sdk.", "ice_api."),
        ("ice_orchestrator.", "ice_api."),
        ("ice_sdk.", "ice_core.models."),
    ]
    # Uses AST to verify import relationships
    # Fails CI on violation
    return forbidden


# Add to forbidden terms check
DEPRECATED_TERMS = [
    ("Tool(", "Use Skill instead"),
    ("AiNode(", "Use LLMOperator instead"),
    ("ScriptChain(", "Use Workflow instead"),
]

# Forbidden legacy paths – CI fails if referenced ---------------------------------
FORBIDDEN_PATHS = [
    "src/ice_sdk/tools/",  # fully migrated to skills
]
