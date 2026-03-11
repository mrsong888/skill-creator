from pathlib import Path

import yaml

from src.skill.types import Skill


def parse_skill_md(skill_md_path: Path) -> Skill:
    """Parse a SKILL.md file into a Skill object."""
    text = skill_md_path.read_text(encoding="utf-8")
    frontmatter = {}
    content = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                frontmatter = {}
            content = parts[2].strip()

    name = frontmatter.get("name", skill_md_path.parent.name)

    return Skill(
        name=name,
        description=frontmatter.get("description", ""),
        license=frontmatter.get("license", ""),
        allowed_tools=frontmatter.get("allowed-tools", []),
        content=content,
        path=str(skill_md_path.parent),
    )


def scan_skills_directory(skills_dir: Path, category: str = "custom") -> list[Skill]:
    """Scan a directory for skill subdirectories containing SKILL.md."""
    skills = []
    if not skills_dir.exists():
        return skills
    for entry in sorted(skills_dir.iterdir()):
        skill_md = entry / "SKILL.md"
        if entry.is_dir() and skill_md.exists():
            skill = parse_skill_md(skill_md)
            skill.category = category
            skills.append(skill)
    return skills
