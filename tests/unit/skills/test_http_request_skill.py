import httpx
import pytest

from ice_sdk.skills.web import HttpRequestSkill


@pytest.mark.asyncio
async def test_http_request_skill(monkeypatch):
    async def fake_get(self, url: str, params=None):  # noqa: D401
        class _Resp:
            status_code = 200
            headers = {"content-type": "text/plain"}
            content = b"hello world"

        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)  # type: ignore[arg-type]

    skill = HttpRequestSkill()
    res = await skill.execute({"url": "https://example.com"})
    assert res["status_code"] == 200
    assert res["body"].startswith("hello")
