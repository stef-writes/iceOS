"""Event subsystem for iceOS.

The dispatcher provides a *non-blocking* pub/sub mechanism so components like
CLI commands can emit structured events (e.g. for webhooks, metrics) without
introducing tight coupling or blocking IO.
"""

from __future__ import annotations

from .dispatcher import Subscriber, publish, subscribe  # – re-export
from .models import CLICommandEvent, EventEnvelope  # – re-export

__all__ = [
    "CLICommandEvent",
    "EventEnvelope",
    "publish",
    "subscribe",
    "Subscriber",
]
