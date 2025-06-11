class ScriptChainError(Exception):
    """Base exception class for ScriptChain errors"""

    pass


class CircularDependencyError(ScriptChainError):
    """Exception raised when circular dependencies are detected"""

    pass
