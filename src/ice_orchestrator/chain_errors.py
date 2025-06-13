class ScriptChainError(Exception):
    """Base exception class for ScriptChain errors"""

    pass


class CircularDependencyError(ScriptChainError):
    """Exception raised when circular dependencies are detected"""

    pass


# ---------------------------------------------------------------------------
# Backwards-compatibility alias ---------------------------------------------
# ---------------------------------------------------------------------------
# Historically the code imported *ChainError* from this module.  Preserve the
# name so external modules do not break.

ChainError = ScriptChainError  # type: ignore[assignment]
