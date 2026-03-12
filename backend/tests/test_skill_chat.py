"""Tests for skill chat endpoint and helpers."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.skill_chat import (
    build_file_blocks,
    parse_file_updates,
    read_skill_md_files,
    validate_file_path,
)


@pytest.fixture
def skill_dir():
    """Create a temporary skill directory with sample files."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_path = Path(tmp) / "test-skill"
        skill_path.mkdir()

        (skill_path / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Skill\n\nSome content.\n",
            encoding="utf-8",
        )

        ref_dir = skill_path / "reference"
        ref_dir.mkdir()
        (ref_dir / "plan.md").write_text("# Plan Rules\n\nStep 1: Do stuff.\n", encoding="utf-8")
        (ref_dir / "work.md").write_text("# Work Rules\n\nWrite code.\n", encoding="utf-8")

        yield skill_path


class TestReadSkillMdFiles:
    def test_reads_all_md_files(self, skill_dir: Path):
        files = read_skill_md_files(skill_dir)
        assert "SKILL.md" in files
        assert "reference/plan.md" in files
        assert "reference/work.md" in files
        assert len(files) == 3

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = read_skill_md_files(Path(tmp))
            assert files == {}

    def test_ignores_non_md_files(self, skill_dir: Path):
        (skill_dir / "config.json").write_text("{}", encoding="utf-8")
        files = read_skill_md_files(skill_dir)
        assert "config.json" not in files


class TestValidateFilePath:
    def test_valid_skill_md(self, skill_dir: Path):
        result = validate_file_path("SKILL.md", skill_dir)
        assert result is not None
        assert result.name == "SKILL.md"

    def test_valid_reference_file(self, skill_dir: Path):
        result = validate_file_path("reference/plan.md", skill_dir)
        assert result is not None

    def test_rejects_non_md(self, skill_dir: Path):
        result = validate_file_path("config.json", skill_dir)
        assert result is None

    def test_rejects_path_traversal_dotdot(self, skill_dir: Path):
        result = validate_file_path("../../../etc/passwd", skill_dir)
        assert result is None

    def test_rejects_absolute_path(self, skill_dir: Path):
        result = validate_file_path("/etc/passwd.md", skill_dir)
        assert result is None

    def test_rejects_dotdot_in_middle(self, skill_dir: Path):
        result = validate_file_path("reference/../../outside.md", skill_dir)
        assert result is None


class TestParseFileUpdates:
    def test_no_file_tags(self):
        text = "Just a normal response with no file modifications."
        updates = parse_file_updates(text)
        assert updates == []

    def test_single_file_tag(self):
        text = '''Here is the updated file:

<file path="SKILL.md">
---
name: test-skill
description: Updated skill
---

# Updated Skill
</file>

Done!'''
        updates = parse_file_updates(text)
        assert len(updates) == 1
        assert updates[0][0] == "SKILL.md"
        assert "Updated Skill" in updates[0][1]

    def test_multiple_file_tags(self):
        text = '''Updated two files:

<file path="SKILL.md">
---
name: test
description: Test
---
# Test
</file>

<file path="reference/plan.md">
# Plan
Step 1
</file>'''
        updates = parse_file_updates(text)
        assert len(updates) == 2
        assert updates[0][0] == "SKILL.md"
        assert updates[1][0] == "reference/plan.md"

    def test_single_quotes(self):
        text = "<file path='test.md'>content</file>"
        updates = parse_file_updates(text)
        assert len(updates) == 1
        assert updates[0][0] == "test.md"


class TestBuildFileBlocks:
    def test_builds_blocks(self):
        files = {"SKILL.md": "# Skill", "reference/plan.md": "# Plan"}
        result = build_file_blocks(files)
        assert '<file path="SKILL.md">' in result
        assert '<file path="reference/plan.md">' in result

    def test_sorted_order(self):
        files = {"z.md": "Z", "a.md": "A"}
        result = build_file_blocks(files)
        a_pos = result.index("a.md")
        z_pos = result.index("z.md")
        assert a_pos < z_pos


class TestSkillChatEndpoints:
    @pytest.mark.asyncio
    async def test_chat_skill_not_found_returns_404(self):
        from src.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/skills/nonexistent-skill/chat",
                json={"message": "hello", "history": []},
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_files_skill_not_found_returns_404(self):
        from src.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/skills/nonexistent-skill/files")
        assert response.status_code == 404
