from pathlib import Path


def generate_skill_draft(name: str, description: str, content: str, allowed_tools: list[str] | None = None) -> str:
    """Generate a SKILL.md file content from structured input."""
    frontmatter_lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
    ]
    if allowed_tools:
        frontmatter_lines.append("allowed-tools:")
        for tool in allowed_tools:
            frontmatter_lines.append(f"  - {tool}")
    frontmatter_lines.append("---")
    frontmatter_lines.append("")
    frontmatter_lines.append(content)
    return "\n".join(frontmatter_lines)


def save_skill_draft(workspace_dir: Path, skill_md_content: str, name: str) -> Path:
    """Save a skill draft to the workspace."""
    draft_dir = workspace_dir / "skill-draft" / name
    draft_dir.mkdir(parents=True, exist_ok=True)
    skill_path = draft_dir / "SKILL.md"
    skill_path.write_text(skill_md_content, encoding="utf-8")
    return draft_dir
