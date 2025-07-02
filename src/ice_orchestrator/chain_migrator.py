"""Helpers for migrating ScriptChain JSON between versions.

Currently a no-op stub – future versions will contain actual migration logic.
"""

from typing import Any, Dict


class ChainMigrator:  # noqa: D101 – public helper stub
    """Utility class responsible for migrating ScriptChain payloads.

    The public interface is intentionally minimal so we can ship the stub
    quickly and iterate without breaking existing callers.
    """

    @classmethod
    async def migrate(
        cls, chain_json: Dict[str, Any], target_version: str
    ) -> Dict[str, Any]:
        """Migrate *chain_json* in-place to *target_version*.

        The method raises :class:`NotImplementedError` when the requested
        conversion path has not been implemented yet.  Callers SHOULD catch
        the exception and decide whether to abort execution or fall back to a
        compatibility mode.
        """

        current_version: str = chain_json.get("version", "1.0.0")
        if current_version == target_version:
            return chain_json

        # Future: dispatch to registered *upgrade* / *downgrade* functions.
        raise NotImplementedError(
            f"Migration path {current_version} ➜ {target_version} not implemented"
        )
