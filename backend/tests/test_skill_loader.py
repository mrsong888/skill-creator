from src.skill.loader import parse_skill_md


def test_parse_skill_md(temp_dir):
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill
license: MIT
allowed-tools:
  - bash
  - read_file
---

# Test Skill

You are a test assistant. Follow these instructions carefully.
""")

    skill = parse_skill_md(skill_dir / "SKILL.md")
    assert skill.name == "test-skill"
    assert skill.description == "A test skill"
    assert skill.license == "MIT"
    assert skill.allowed_tools == ["bash", "read_file"]
    assert "You are a test assistant" in skill.content


def test_parse_skill_md_minimal(temp_dir):
    skill_dir = temp_dir / "minimal"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: minimal
description: Minimal skill
---

Do something simple.
""")

    skill = parse_skill_md(skill_dir / "SKILL.md")
    assert skill.name == "minimal"
    assert skill.allowed_tools == []
    assert "Do something simple" in skill.content


def test_parse_skill_md_no_frontmatter(temp_dir):
    skill_dir = temp_dir / "nofm"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Just content\n\nNo frontmatter here.")

    skill = parse_skill_md(skill_dir / "SKILL.md")
    assert skill.name == "nofm"
    assert "Just content" in skill.content
