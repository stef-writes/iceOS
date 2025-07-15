import asyncio

import pytest

from ice_sdk.events.dispatcher import publish, subscribe
from ice_sdk.events.models import CLICommandEvent


@pytest.mark.asyncio
async def test_publish_subscribe_roundtrip():
    received: list[str] = []

    async def _handler(env):  # type: ignore[missing-return-type-doc]
        received.append(env.name)

    subscribe("test.event", _handler)

    await publish("test.event", CLICommandEvent(command="x", status="completed"))

    # Give the event loop a tiny slice so create_task callbacks execute
    await asyncio.sleep(0.05)

    assert received == ["test.event"]
