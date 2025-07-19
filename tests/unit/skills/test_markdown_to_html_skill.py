import pytest

from ice_sdk.skills.system import MarkdownToHTMLSkill


@pytest.mark.asyncio
async def test_markdown_to_html():
    md = "# Title\nContent"
    res = await MarkdownToHTMLSkill().execute({"markdown": md})
    assert "<h1>" in res["html"]
