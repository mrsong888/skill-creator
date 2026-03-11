from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.skill.manager import SkillManager


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def skill_dirs(temp_dir):
    public = temp_dir / "public"
    custom = temp_dir / "custom"
    public.mkdir()
    custom.mkdir()
    sd = public / "test-skill"
    sd.mkdir()
    (sd / "SKILL.md").write_text("---\nname: test-skill\ndescription: Test\n---\n\nContent.")
    return public, custom


async def test_list_skills(client, skill_dirs):
    public, custom = skill_dirs
    with patch("src.api.skills.get_skill_manager", return_value=SkillManager(public, custom)):
        response = await client.get("/api/skills")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-skill"


async def test_get_skill(client, skill_dirs):
    public, custom = skill_dirs
    with patch("src.api.skills.get_skill_manager", return_value=SkillManager(public, custom)):
        response = await client.get("/api/skills/test-skill")
    assert response.status_code == 200
    assert response.json()["name"] == "test-skill"


async def test_get_skill_not_found(client, skill_dirs):
    public, custom = skill_dirs
    with patch("src.api.skills.get_skill_manager", return_value=SkillManager(public, custom)):
        response = await client.get("/api/skills/nonexistent")
    assert response.status_code == 404


async def test_update_skill_enabled(client, skill_dirs):
    public, custom = skill_dirs
    config_path = skill_dirs[0].parent / "ext.json"
    mgr = SkillManager(public, custom, extensions_config_path=config_path)
    with patch("src.api.skills.get_skill_manager", return_value=mgr):
        response = await client.put("/api/skills/test-skill", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["enabled"] is False


async def test_delete_public_skill_fails(client, skill_dirs):
    public, custom = skill_dirs
    with patch("src.api.skills.get_skill_manager", return_value=SkillManager(public, custom)):
        response = await client.delete("/api/skills/test-skill")
    assert response.status_code == 400
