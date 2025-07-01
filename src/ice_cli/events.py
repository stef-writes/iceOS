"""Shared event utilities for ice_cli.

The helper functions in this module are intentionally side-effect-free so they
can be imported by sub-modules (e.g. *commands.tool*) without triggering Typer
app initialisation or causing circular imports back to *ice_cli.cli*.
"""
from __future__ import annotations

# stdlib
import asyncio

# 3rd-party
from pydantic import BaseModel

from ice_cli.context import get_ctx  # noqa: WPS433

# Project
from ice_sdk.events.dispatcher import publish  # noqa: WPS433

__all__ = ["_emit_event"]


def _emit_event(name: str, payload: BaseModel) -> None:  # noqa: D401 – helper
    """Safely publish *payload* under *name* respecting the --no-events flag.

    The function is **non-blocking**: it schedules the actual *publish* call on
    the event loop with :pyfunc:`asyncio.create_task` so the calling CLI command
    returns control immediately.
    """

    try:
        # Honour the --no-events flag stored on the global CLIContext.
        if not get_ctx().emit_events:  # type: ignore[attr-defined]
            return
        # Dispatch in the background – any errors are deliberately swallowed so
        # telemetry never breaks the user-facing command.
        asyncio.create_task(publish(name, payload))
    except Exception:  # noqa: BLE001 – best-effort only
        pass 