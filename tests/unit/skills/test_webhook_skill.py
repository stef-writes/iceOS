import types

import httpx
import pytest

from ice_sdk.skills.web import WebhookSkill


class _CtxStub:
    def __init__(self):
        self.metadata = {"foo": "bar"}


@pytest.mark.asyncio
async def test_webhook_skill(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):  # noqa: D401
        class _Resp:
            status_code = 204

            def raise_for_status(self):
                return None

        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)  # type: ignore[arg-type]
    res = await WebhookSkill().execute({"url": "https://example.com", "ctx": _CtxStub()})
    assert res["status_code"] == 204 