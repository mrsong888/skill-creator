from pathlib import Path

from src.skill.manager import SkillManager


def _create_skill(base: Path, category: str, name: str, desc: str = "Test"):
    d = base / category / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\nContent for {name}.")


def test_list_skills(temp_dir):
    _create_skill(temp_dir, "public", "reviewer", "Code reviewer")
    _create_skill(temp_dir, "custom", "my-tool", "My custom tool")

    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    skills = mgr.list_skills()
    names = [s.name for s in skills]
    assert "reviewer" in names
    assert "my-tool" in names


def test_get_skill(temp_dir):
    _create_skill(temp_dir, "public", "reviewer", "Code reviewer")
    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    skill = mgr.get_skill("reviewer")
    assert skill is not None
    assert skill.description == "Code reviewer"


def test_get_skill_not_found(temp_dir):
    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    assert mgr.get_skill("nonexistent") is None


def test_enable_disable_skill(temp_dir):
    _create_skill(temp_dir, "custom", "my-tool")
    config_path = temp_dir / "extensions.json"

    mgr = SkillManager(
        public_path=temp_dir / "public",
        custom_path=temp_dir / "custom",
        extensions_config_path=config_path,
    )
    mgr.set_enabled("my-tool", False)
    skills = mgr.list_skills()
    my_tool = next(s for s in skills if s.name == "my-tool")
    assert my_tool.enabled is False

    mgr.set_enabled("my-tool", True)
    skills = mgr.list_skills()
    my_tool = next(s for s in skills if s.name == "my-tool")
    assert my_tool.enabled is True


def test_uninstall_custom_skill(temp_dir):
    _create_skill(temp_dir, "custom", "my-tool")
    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    assert mgr.uninstall_skill("my-tool") is True
    assert mgr.get_skill("my-tool") is None


def test_uninstall_public_skill_fails(temp_dir):
    _create_skill(temp_dir, "public", "reviewer")
    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    assert mgr.uninstall_skill("reviewer") is False
