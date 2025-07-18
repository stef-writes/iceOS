# Legacy stub import is safe but prefer the new base_workflow naming
from .base_workflow import BaseWorkflow as BaseScriptChain, FailurePolicy  # type: ignore

__all__ = [
    "BaseScriptChain",  # alias to BaseWorkflow
    "FailurePolicy",
]
