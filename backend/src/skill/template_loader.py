import logging
import os
from pathlib import Path

import yaml

from src.skill.template_types import SkillTemplate, TemplateVariable

logger = logging.getLogger(__name__)

# Module-level mtime cache
_templates_cache: list[SkillTemplate] | None = None
_templates_dir_mtime: float = 0


def parse_template_yaml(path: str | Path) -> SkillTemplate:
    """Parse a template YAML file into a SkillTemplate."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Template file must contain a YAML mapping: {path}")

    for field in ("name", "description", "category", "version", "prompt"):
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in template: {path}")

    variables = []
    for var_data in data.get("variables", []):
        if not isinstance(var_data, dict) or "name" not in var_data:
            continue
        variables.append(
            TemplateVariable(
                name=var_data["name"],
                type=var_data.get("type", "string"),
                required=var_data.get("required", True),
                default=var_data.get("default"),
                description=var_data.get("description", ""),
                options=var_data.get("options", []),
            )
        )

    frontmatter = data.get("frontmatter", {})
    if not isinstance(frontmatter, dict):
        frontmatter = {}

    files = data.get("files", {})
    if not isinstance(files, dict):
        files = {}

    return SkillTemplate(
        name=data["name"],
        description=data["description"],
        category=data.get("category", "general"),
        version=data.get("version", "1.0"),
        llm_enhance=data.get("llm_enhance", False),
        variables=variables,
        frontmatter=frontmatter,
        prompt=data["prompt"],
        llm_enhance_prompt=data.get("llm_enhance_prompt", ""),
        path=str(path),
        files=files,
    )


def scan_templates_directory(directory: str | Path) -> list[SkillTemplate]:
    """Scan a directory for template YAML files."""
    global _templates_cache, _templates_dir_mtime

    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        return []

    current_mtime = os.path.getmtime(directory)
    if _templates_cache is not None and current_mtime == _templates_dir_mtime:
        return _templates_cache

    templates = []
    for yaml_file in sorted(directory.glob("*.yaml")):
        try:
            templates.append(parse_template_yaml(yaml_file))
        except Exception as e:
            logger.warning(f"Failed to parse template {yaml_file}: {e}")

    for yml_file in sorted(directory.glob("*.yml")):
        try:
            templates.append(parse_template_yaml(yml_file))
        except Exception as e:
            logger.warning(f"Failed to parse template {yml_file}: {e}")

    _templates_cache = templates
    _templates_dir_mtime = current_mtime
    return templates


def invalidate_templates_cache() -> None:
    global _templates_cache, _templates_dir_mtime
    _templates_cache = None
    _templates_dir_mtime = 0
