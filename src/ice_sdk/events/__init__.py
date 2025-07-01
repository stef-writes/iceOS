"""Event subsystem for iceOS.

The dispatcher provides a *non-blocking* pub/sub mechanism so components like
CLI commands can emit structured events (e.g. for webhooks, metrics) without
introducing tight coupling or blocking IO.
"""

from __future__ import annotations

from .models import CLICommandEvent, EventEnvelope  # noqa: F401 – re-export
from .dispatcher import publish, subscribe, Subscriber  # noqa: F401 – re-export

__all__ = [
    "CLICommandEvent",
    "EventEnvelope",
    "publish",
    "subscribe",
    "Subscriber",
] 