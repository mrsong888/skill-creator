import re

import yaml


def validate_skill_md(content: str) -> tuple[bool, str]:
    """Validate SKILL.md content format.

    Returns:
        Tuple of (is_valid, message).
    """
    if not content or not content.strip():
        return False, "Content is empty"

    if not content.startswith("---"):
        return False, "No YAML frontmatter found (must start with ---)"

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format (missing closing ---)"

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML mapping"
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    # Validate name
    name = frontmatter.get("name")
    if not name:
        return False, "Missing required field 'name' in frontmatter"
    if not isinstance(name, str):
        return False, f"'name' must be a string, got {type(name).__name__}"
    name = name.strip()
    if not name:
        return False, "'name' cannot be empty"
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name '{name}' must be kebab-case (lowercase letters, digits, and hyphens only)"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
    if len(name) > 64:
        return False, f"Name is too long ({len(name)} chars, max 64)"

    # Validate description
    description = frontmatter.get("description")
    if not description:
        return False, "Missing required field 'description' in frontmatter"
    if not isinstance(description, str):
        return False, f"'description' must be a string, got {type(description).__name__}"
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(description) > 1024:
        return False, f"Description is too long ({len(description)} chars, max 1024)"

    # Validate allowed-tools
    allowed_tools = frontmatter.get("allowed-tools")
    if allowed_tools is not None and not isinstance(allowed_tools, list):
        return False, "'allowed-tools' must be a list"

    # Check body
    body = content[match.end():].strip()
    if not body:
        return False, "Markdown body is empty (must contain content after frontmatter)"

    return True, "Valid"
