"""Tests for the skill template system."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.skill.template_loader import invalidate_templates_cache, parse_template_yaml, scan_templates_directory
from src.skill.template_manager import TemplateManager
from src.skill.template_types import SkillTemplate, TemplateVariable
from src.skill.validator import validate_skill_md

MINIMAL_TEMPLATE = {
    "name": "test-template",
    "description": "A test template",
    "category": "testing",
    "version": "1.0",
    "llm_enhance": False,
    "variables": [
        {"name": "project", "type": "string", "required": True, "description": "Project name"},
        {"name": "tags", "type": "list", "required": False, "default": ["a", "b"], "description": "Tags"},
    ],
    "frontmatter": {"name": "${project}-skill", "description": "Skill for ${project}"},
    "prompt": "# ${project}\n\nHello ${project}!\n\nTags:\n${tags}",
}


def _write_template(tmpdir: Path, name: str, data: dict) -> Path:
    path = tmpdir / f"{name}.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# --- Template Types ---


class TestTemplateTypes:
    def test_variable_defaults(self):
        v = TemplateVariable(name="x")
        assert v.required is True
        assert v.default is None
        assert v.options == []

    def test_template_fields(self):
        t = SkillTemplate(
            name="t", description="d", category="c", version="1",
            llm_enhance=False, variables=[], frontmatter={}, prompt="p",
        )
        assert t.llm_enhance_prompt == ""


# --- Template Loader ---


class TestTemplateLoader:
    def test_parse_yaml(self, temp_dir):
        path = _write_template(temp_dir, "t1", MINIMAL_TEMPLATE)
        t = parse_template_yaml(path)
        assert t.name == "test-template"
        assert len(t.variables) == 2

    def test_parse_missing_field(self, temp_dir):
        path = _write_template(temp_dir, "bad", {"name": "bad", "description": "d"})
        with pytest.raises(ValueError, match="Missing required field"):
            parse_template_yaml(path)

    def test_parse_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_template_yaml("/nonexistent.yaml")

    def test_scan_directory(self, temp_dir):
        invalidate_templates_cache()
        _write_template(temp_dir, "a", MINIMAL_TEMPLATE)
        _write_template(temp_dir, "b", {**MINIMAL_TEMPLATE, "name": "b-template"})
        assert len(scan_templates_directory(temp_dir)) == 2

    def test_scan_nonexistent(self):
        invalidate_templates_cache()
        assert scan_templates_directory("/nonexistent") == []


# --- Template Manager ---


class TestTemplateManager:
    def setup_method(self):
        invalidate_templates_cache()
        self.tmpdir = Path(tempfile.mkdtemp())
        _write_template(self.tmpdir, "test", MINIMAL_TEMPLATE)
        self.mgr = TemplateManager(self.tmpdir)

    def test_list(self):
        assert len(self.mgr.list_templates()) == 1

    def test_get(self):
        assert self.mgr.get_template("test-template") is not None

    def test_get_not_found(self):
        assert self.mgr.get_template("nope") is None

    def test_render(self):
        content = self.mgr.render("test-template", {"project": "myapp"})
        assert "myapp" in content
        assert "- a" in content
        assert "- b" in content

    def test_render_list_override(self):
        content = self.mgr.render("test-template", {"project": "x", "tags": ["x", "y"]})
        assert "- x" in content
        assert "- y" in content

    def test_render_missing_required(self):
        with pytest.raises(ValueError, match="Missing required"):
            self.mgr.render("test-template", {})

    def test_render_frontmatter(self):
        content = self.mgr.render("test-template", {"project": "demo"})
        assert "demo-skill" in content
        assert "Skill for demo" in content


# --- Validator ---


class TestValidator:
    def test_valid(self):
        ok, _ = validate_skill_md("---\nname: my-skill\ndescription: test\n---\n\n# Content\n")
        assert ok

    def test_empty(self):
        ok, msg = validate_skill_md("")
        assert not ok and "empty" in msg.lower()

    def test_no_frontmatter(self):
        ok, msg = validate_skill_md("# No frontmatter")
        assert not ok

    def test_missing_name(self):
        ok, _ = validate_skill_md("---\ndescription: x\n---\n\n# C\n")
        assert not ok

    def test_missing_description(self):
        ok, _ = validate_skill_md("---\nname: x\n---\n\n# C\n")
        assert not ok

    def test_bad_name(self):
        ok, msg = validate_skill_md("---\nname: Bad Name!\ndescription: x\n---\n\n# C\n")
        assert not ok and "kebab" in msg.lower()

    def test_name_too_long(self):
        ok, _ = validate_skill_md(f"---\nname: {'a' * 65}\ndescription: x\n---\n\n# C\n")
        assert not ok

    def test_angle_brackets(self):
        ok, _ = validate_skill_md("---\nname: x\ndescription: <bad>\n---\n\n# C\n")
        assert not ok

    def test_empty_body(self):
        ok, msg = validate_skill_md("---\nname: x\ndescription: y\n---\n")
        assert not ok and "body" in msg.lower()

    def test_allowed_tools_string(self):
        ok, _ = validate_skill_md("---\nname: x\ndescription: y\nallowed-tools: bash\n---\n\n# C\n")
        assert not ok

    def test_allowed_tools_list(self):
        ok, _ = validate_skill_md("---\nname: x\ndescription: y\nallowed-tools:\n  - bash\n---\n\n# C\n")
        assert ok
