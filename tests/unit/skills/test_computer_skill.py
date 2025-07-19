import sys
from types import SimpleNamespace

import pytest

from ice_sdk.skills.system import ComputerSkill


@pytest.fixture(autouse=True)
def fake_pyautogui(monkeypatch):
    # Provide a minimal fake pyautogui module
    fake = SimpleNamespace(
        click=lambda *a, **k: None,
        typewrite=lambda *a, **k: None,
        scroll=lambda *a, **k: None,
        screenshot=lambda: SimpleNamespace(save=lambda buf, format=None: None),
    )
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    yield
    sys.modules.pop("pyautogui", None)


@pytest.mark.asyncio
async def test_computer_skill_click():
    skill = ComputerSkill()
    res = await skill.execute({"action": "click", "x": 10, "y": 20})
    assert res["success"] is True


@pytest.mark.asyncio
async def test_computer_skill_invalid_action():
    skill = ComputerSkill()
    with pytest.raises(Exception):
        await skill.execute({"action": "invalid"})
