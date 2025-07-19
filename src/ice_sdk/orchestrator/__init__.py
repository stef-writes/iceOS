# Legacy stub import is safe but prefer the new base_workflow naming
from .base_workflow import BaseWorkflow as BaseScriptChain  # type: ignore
from .base_workflow import FailurePolicy

__all__ = [
    "BaseScriptChain",  # alias to BaseWorkflow
    "FailurePolicy",
]
