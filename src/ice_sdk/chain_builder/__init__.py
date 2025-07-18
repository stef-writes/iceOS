# Preferred API
from .workflow_builder import WorkflowBuilder, WorkflowDraft, Question

# Legacy aliases for backward-compat ------------------------------------------------
from .workflow_builder import BuilderEngine as BuilderEngine  # type: ignore
from .workflow_builder import ChainDraft as ChainDraft  # type: ignore

__all__ = [
    "WorkflowBuilder",
    "WorkflowDraft",
    # Legacy
    "BuilderEngine",
    "ChainDraft",
    "Question",
]
