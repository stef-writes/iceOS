"""Register built-in (core) chains.

The *ice_sdk* package purposely ships **no** concrete business chains so that
application code can decide what to register.  Example/demo chains now live in
the separate ``samples`` package and should be registered by the caller (e.g.
CLI command or application startup code) rather than from within the SDK.
"""


def register_builtin_chains() -> None:  # noqa: D401
    """No-op placeholder.

    Keeping the function allows external code to import and call it without
    breaking, but it intentionally performs **no** registrations.
    """

    # Intentionally empty – add real production chains here in the future.
    return None
