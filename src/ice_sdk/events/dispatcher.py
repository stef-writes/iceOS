"""Minimal async event dispatcher used by iceOS CLI & runtime.

Design goals:
1. **Non-blocking** – publishes never block callers; callbacks are scheduled via
   ``asyncio.create_task``.
2. **In-process** – no external broker; suitable for unit tests and simple
   extensions like WebhookEmitterTool.
3. **Tiny surface** – just ``subscribe`` and ``publish`` so we can replace it
   later with a more powerful bus without large refactors.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List

from pydantic import BaseModel

from .models import EventEnvelope

Subscriber = Callable[[EventEnvelope], Awaitable[None]]

# Internal registry ---------------------------------------------------------
_subscribers: Dict[str, List[Subscriber]] = defaultdict(list)


def subscribe(event_name: str, callback: Subscriber) -> None:
    """Register *callback* for *event_name*."""

    _subscribers[event_name].append(callback)


async def publish(event_name: str, payload: BaseModel) -> None:
    """Publish *payload* under *event_name* without blocking the caller."""

    envelope = EventEnvelope(name=event_name, payload=payload)

    for cb in list(_subscribers.get(event_name, [])):

        async def _run_callback(callback: Subscriber, env: EventEnvelope) -> None:
            try:
                await callback(env)
            except Exception:
                pass

        asyncio.create_task(_run_callback(cb, envelope))
