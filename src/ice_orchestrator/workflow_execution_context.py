from typing import Any, Dict, Optional


class WorkflowExecutionContext:
    """
    Holds workflow-wide execution settings, output format requirements, and preferences for ScriptChain orchestration.
    """

    def __init__(
        self,
        mode: str = "auto",
        require_json_output: bool = False,
        strict_validation: bool = False,
        user_preferences: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        self.mode = mode  # e.g., 'tool-calling', 'chat', 'summarization', etc.
        self.require_json_output = require_json_output
        self.strict_validation = strict_validation
        self.user_preferences = user_preferences or {}
        # Store any additional context fields
        for k, v in kwargs.items():
            setattr(self, k, v)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "require_json_output": self.require_json_output,
            "strict_validation": self.strict_validation,
            "user_preferences": self.user_preferences,
            **{
                k: v
                for k, v in self.__dict__.items()
                if k
                not in {
                    "mode",
                    "require_json_output",
                    "strict_validation",
                    "user_preferences",
                }
            },
        }
